import os
import json
from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
import httpx
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

class AzureDocumentIntelligenceService:
    def __init__(self):
        self.endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        self.api_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_KEY")
        
        if not self.endpoint or not self.api_key:
            raise ValueError("Azure Document Intelligence credentials not configured")
        
        self.client = DocumentIntelligenceClient(
            endpoint=self.endpoint,
            credential=AzureKeyCredential(self.api_key)
        )

    async def extract_receipt_data(self, image_url: str) -> Dict[str, Any]:
        """Extract data from receipt image using Azure Document Intelligence"""
        try:
            # Use URL directly with AnalyzeDocumentRequest
            poller = self.client.begin_analyze_document(
                "prebuilt-receipt", AnalyzeDocumentRequest(url_source=image_url)
            )
            result = poller.result()

            extracted_data = {
                "merchant_name": "",
                "total_amount": 0.0,
                "date": datetime.now().isoformat(),
                "items": [],
                "tax_amount": 0.0,
                "subtotal": 0.0
            }

            # Process receipts following Azure example pattern
            for receipt in result.documents:
                # Merchant name
                merchant_name = receipt.fields.get("MerchantName")
                if merchant_name:
                    extracted_data["merchant_name"] = merchant_name.value_string
                
                # Transaction date
                transaction_date = receipt.fields.get("TransactionDate")
                if transaction_date:
                    extracted_data["date"] = transaction_date.value_date.isoformat()
                
                # Total amount
                total = receipt.fields.get("Total")
                if total:
                    extracted_data["total_amount"] = float(total.value_currency.amount)
                
                # Tax amount
                tax = receipt.fields.get("TotalTax")
                if tax:
                    extracted_data["tax_amount"] = float(tax.value_currency.amount)
                
                # Subtotal
                subtotal = receipt.fields.get("Subtotal")
                if subtotal:
                    extracted_data["subtotal"] = float(subtotal.value_currency.amount)

                # Extract line items
                if receipt.fields.get("Items"):
                    items = []
                    for item in receipt.fields.get("Items").value_array:
                        item_data = {}
                        
                        item_description = item.value_object.get("Description")
                        if item_description:
                            item_data["name"] = item_description.value_string
                        
                        item_quantity = item.value_object.get("Quantity")
                        if item_quantity:
                            item_data["quantity"] = item_quantity.value_number
                        
                        item_price = item.value_object.get("Price")
                        if item_price:
                            item_data["unit_price"] = float(item_price.value_currency.amount)
                        
                        item_total_price = item.value_object.get("TotalPrice")
                        if item_total_price:
                            item_data["price"] = float(item_total_price.value_currency.amount)
                        
                        items.append(item_data)
                    extracted_data["items"] = items

            return extracted_data

        except Exception as e:
            raise Exception(f"Failed to extract receipt data: {str(e)}")

class AzureOpenAIService:
    def __init__(self):
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")
        
        if not self.endpoint or not self.api_key:
            raise ValueError("Azure OpenAI credentials not configured")
        
        self.client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version="2024-02-15-preview"
        )

    async def validate_claim_data(self, claim_data: Dict[str, Any], user_context: Optional[Dict[str, Any]] = None) -> str:
        """Validate claim data using AI"""
        try:
            prompt = f"""
            Validate this expense claim data:
            {json.dumps(claim_data, indent=2)}
            
            User context: {json.dumps(user_context or {}, indent=2)}
            
            Check for:
            1. Reasonable amounts for business expenses
            2. Valid business expense categories
            3. Complete and consistent information
            4. Policy compliance (reasonable amounts, business-related)
            
            Respond with validation results and any questions or suggestions for the user.
            Keep the response conversational and helpful.
            """
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant that validates expense claims for business travelers."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            return response.choices[0].message.content

        except Exception as e:
            raise Exception(f"Failed to validate claim data: {str(e)}")

    async def chat_response(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate AI chat response for claim assistance"""
        try:
            system_prompt = """
            You are a helpful AI assistant for expense claim submissions. You help users:
            1. Upload and process receipt images
            2. Extract and validate expense data
            3. Guide them through the claim submission process
            4. Answer questions about expense policies
            
            Be conversational, helpful, and guide users step by step.
            """
            
            context_info = ""
            if context:
                context_info = f"\nContext: {json.dumps(context, indent=2)}"
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{message}{context_info}"}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            return response.choices[0].message.content

        except Exception as e:
            return "I'm sorry, I encountered an error. Please try again or contact support if the issue persists."