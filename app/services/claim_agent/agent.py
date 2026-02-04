import os
import json
import logging
from typing import TypedDict, Annotated, Sequence, Any, List, Dict

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
    SystemMessage,
)
from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from sqlalchemy.orm import Session

from app.services.claim_agent.tools import get_claim_tools

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI expense claims assistant for MSafiri. You help users manage their business expense claims through natural conversation.

Your capabilities:
- Create new expense claims
- Add line items (expenses) to claims
- List and search existing claims
- Show detailed claim information
- Submit draft claims for approval
- Extract data from receipt images using OCR
- Provide spending analytics and summaries

Guidelines:
- Be conversational and helpful. Guide users step by step.
- When a user mentions an expense, proactively create a claim and add the item.
- When creating a claim, use the expense description and amount from the user's message.
- For dates, if the user doesn't specify, use today's date.
- For categories, infer from context: meals, transport, accommodation, supplies, or other.
- Always confirm what you've done after using a tool.
- If the user uploads a receipt image, use extract_receipt to get the data, then offer to create a claim from it.
- Keep monetary amounts as numbers (not strings).
- When showing claims or analytics, present the data in a clear, readable format.
- If the user's intent is unclear, ask a clarifying question rather than guessing.

Today's date is {today}.
"""


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], lambda x, y: list(x) + list(y)]


def _get_llm():
    """Create the Azure OpenAI LLM instance."""
    return AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
        temperature=0.3,
    )


def build_agent_graph(db: Session, user_id: int):
    """Build a LangGraph agent with claim tools bound to the given user/session."""
    tools = get_claim_tools(db, user_id)
    llm = _get_llm()
    llm_with_tools = llm.bind_tools(tools)

    def agent_node(state: AgentState) -> dict:
        """Invoke the LLM with the current message history."""
        messages = list(state["messages"])
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentState) -> str:
        """Check if the agent wants to call tools or is done."""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    tool_node = ToolNode(tools)

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


async def run_agent(
    db: Session,
    user_id: int,
    message_history: List[Dict[str, Any]],
    user_message: str,
    image_url: str | None = None,
) -> dict:
    """Run the agent with a user message and return the response.

    Args:
        db: Database session.
        user_id: The authenticated user's ID.
        message_history: Previous messages in LangChain format.
        user_message: The new user message.
        image_url: Optional receipt image URL.

    Returns:
        dict with keys: response (str), tool_results (list of dicts)
    """
    from datetime import date

    graph = build_agent_graph(db, user_id)

    # Build messages list starting with system prompt
    messages: list[BaseMessage] = [
        SystemMessage(content=SYSTEM_PROMPT.format(today=date.today().isoformat()))
    ]

    # Add conversation history
    for msg in message_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            # Reconstruct AIMessage with tool_calls if present
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                messages.append(AIMessage(content=content or "", tool_calls=tool_calls))
            else:
                messages.append(AIMessage(content=content))
        elif role == "tool":
            tool_results = msg.get("tool_results", {})
            tool_call_id = tool_results.get("tool_call_id", "")
            messages.append(
                ToolMessage(content=json.dumps(tool_results.get("result", {})), tool_call_id=tool_call_id)
            )

    # Add the new user message
    content_text = user_message
    if image_url:
        content_text += f"\n\n[User attached a receipt image: {image_url}]"
    messages.append(HumanMessage(content=content_text))

    # Run the agent graph
    logger.info(f"Running agent for user {user_id} with {len(messages)} messages")
    result = await _invoke_graph(graph, messages)

    # Extract the final response and any tool results
    response_text = ""
    tool_results = []

    for msg in result["messages"]:
        if isinstance(msg, AIMessage):
            if msg.content:
                response_text = msg.content
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_results.append({
                        "tool_name": tc["name"],
                        "tool_call_id": tc["id"],
                        "args": tc["args"],
                    })
        elif isinstance(msg, ToolMessage):
            # Find matching tool result entry and add the result
            for tr in tool_results:
                if tr.get("tool_call_id") == msg.tool_call_id:
                    try:
                        tr["result"] = json.loads(msg.content)
                    except (json.JSONDecodeError, TypeError):
                        tr["result"] = msg.content
                    break

    if not response_text:
        response_text = "I've processed your request. Is there anything else you'd like to do?"

    return {
        "response": response_text,
        "tool_results": tool_results,
    }


async def _invoke_graph(graph, messages: list[BaseMessage]) -> dict:
    """Invoke the LangGraph agent. Uses ainvoke for async support."""
    try:
        result = await graph.ainvoke({"messages": messages})
        return result
    except Exception as e:
        logger.error(f"Agent invocation failed: {e}", exc_info=True)
        return {
            "messages": [
                AIMessage(
                    content=f"I'm sorry, I encountered an error processing your request. Please try again. (Error: {str(e)})"
                )
            ]
        }
