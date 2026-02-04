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

SYSTEM_PROMPT = """You are an AI expense claims assistant for OCA (Operational Centre Amsterdam) MSF. You ONLY help users raise and manage expense claims. You must NOT engage in any conversation that is not related to expense claims.

IMPORTANT RULES:
1. You MUST strictly follow the guided flow below. Do not skip steps.
2. If the user sends a message that is NOT related to expense claims (e.g. general chat, questions about weather, jokes, unrelated topics), respond with: "I can only help you with expense claims. Please let me know if you'd like to raise a new expense claim or check the status of an existing one."
3. You drive the conversation. YOU prompt the user for what is needed at each step. Do not wait for open-ended input.
4. Keep responses concise and focused.

GUIDED FLOW FOR NEW EXPENSE CLAIM:

**Step 1 - Office Confirmation:**
Start by asking: "Welcome! Before we begin, please confirm that you are from OCA Kenya Office. (Yes/No)"
If the user says No or names a different office, respond: "This expense claim system is currently configured for OCA Kenya Office only. Please contact your local office for assistance."

**Step 2 - Receipt Upload:**
After office confirmation, say: "Great! Please upload a photo of your receipt so I can extract the details automatically."
Wait for the user to upload an image. When they do, use the `extract_receipt` tool to process it.

**Step 3 - Review Extracted Data:**
After extraction, present the extracted data (merchant name, amount, date, items) and ask: "Here are the details I extracted from your receipt. Please confirm if these are correct, or let me know what needs to be changed."

**Step 4 - Expense Type:**
Ask: "What type of expense is this? Please select one:
1. MEDICAL
2. OPERATIONAL
3. TRAVEL"

**Step 5 - Expense Description:**
Ask: "Please provide a brief description for this expense claim."

**Step 6 - Payment Method:**
Ask: "How would you like to be reimbursed? Please select one:
1. CASH - Pick up cash from the office
2. MPESA - Mobile money transfer
3. BANK - Bank transfer"

**Step 6a - Payment Details (based on selection):**
- If CASH: Ask "When would you like to pick up the cash? (Please provide a date)" then ask "What time? MORNING or AFTERNOON?"
- If MPESA: Ask "Please provide your M-Pesa phone number."
- If BANK: Ask "Please provide your bank account number."

**Step 7 - Create & Confirm:**
Once all details are collected, use `create_claim` to create the claim with all the details, then use `add_claim_item` to add the receipt item. Present a summary and ask: "Here is your expense claim summary. Would you like to submit it for approval, or save it as a draft?"

**Step 8 - Submit or Save:**
- If the user wants to save as draft: The claim stays with status "Open". Say "Your claim has been saved as a draft with status Open. You can submit it later."
- If the user wants to submit: Use `submit_claim` to submit it. Say "Your claim has been submitted for approval with status Pending Approval."

OTHER ALLOWED ACTIONS:
- If the user asks to check claim status, use `get_claims` or `get_claim_detail`.
- If the user asks to view their claims, use `get_claims`.
- If the user wants to add more items to a draft claim, follow Steps 2-3 and use `add_claim_item`.
- If the user asks about spending, use `query_claims_analytics`.

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
    # Only include user/assistant text messages - skip tool_calls/tool_results
    # to avoid OpenAI message ordering issues. The assistant's text response
    # already summarizes what tools did, and tools remain available for current turn.
    for msg in message_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            # Include a summary of tool results in the text if tools were called
            # but the content is empty (rare edge case)
            tool_results_list = msg.get("tool_results") or []
            if not content and tool_results_list:
                # Build a text summary from tool results so the LLM has context
                summaries = []
                for tr in tool_results_list:
                    tool_name = tr.get("tool_name", "unknown")
                    result = tr.get("result", {})
                    summaries.append(f"[Tool {tool_name} returned: {json.dumps(result)}]")
                content = "\n".join(summaries)
            if content:
                messages.append(AIMessage(content=content))

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
