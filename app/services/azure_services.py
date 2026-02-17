import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
import httpx
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

# Set up logging
logger = logging.getLogger(__name__)

class AzureDocumentIntelligenceService:
    def __init__(self):
        self.endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        self.api_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_KEY")
        
        if not self.endpoint or not self.api_key:
            logger.warning("Azure Document Intelligence credentials not configured - service will be unavailable")
            self.client = None
            return
        
        try:
            self.client = DocumentIntelligenceClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.api_key)
            )
            logger.info("Azure Document Intelligence client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Azure Document Intelligence client: {e}")
            self.client = None

    def _sync_extract_receipt(self, image_url: str):
        """Synchronous receipt extraction - runs in thread executor"""
        logger.info("📤 Sending request to Azure Document Intelligence...")
        poller = self.client.begin_analyze_document(
            "prebuilt-receipt", AnalyzeDocumentRequest(url_source=image_url)
        )
        logger.info("⏳ Waiting for analysis to complete...")
        result = poller.result()
        return result

    async def extract_receipt_data(self, image_url: str) -> Dict[str, Any]:
        """Extract data from receipt image using Azure Document Intelligence"""
        logger.info(f"🧾 Starting receipt extraction for URL: {image_url[:100]}...")

        try:
            # Run synchronous Azure SDK call in thread executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._sync_extract_receipt, image_url)
            logger.info(f"✅ Analysis complete. Found {len(result.documents)} documents")

            extracted_data = {
                "merchant_name": "",
                "total_amount": 0.0,
                "date": datetime.now().isoformat(),
                "items": [],
                "tax_amount": 0.0,
                "subtotal": 0.0
            }

            # Process receipts following Azure example pattern
            for idx, receipt in enumerate(result.documents):
                logger.info(f"📋 Processing receipt #{idx + 1}")
                logger.info(f"📋 Receipt type: {receipt.doc_type}")
                logger.info(f"📋 Available fields: {list(receipt.fields.keys()) if receipt.fields else 'None'}")
                
                # Merchant name
                merchant_name = receipt.fields.get("MerchantName")
                if merchant_name:
                    extracted_data["merchant_name"] = merchant_name.value_string
                    logger.info(f"🏪 Merchant: {merchant_name.value_string} (confidence: {merchant_name.confidence})")
                else:
                    logger.warning("⚠️ No merchant name found")
                
                # Transaction date
                transaction_date = receipt.fields.get("TransactionDate")
                if transaction_date:
                    extracted_data["date"] = transaction_date.value_date.isoformat()
                    logger.info(f"📅 Date: {transaction_date.value_date} (confidence: {transaction_date.confidence})")
                else:
                    logger.warning("⚠️ No transaction date found")
                
                # Total amount and currency
                total = receipt.fields.get("Total")
                if total:
                    extracted_data["total_amount"] = float(total.value_currency.amount)
                    # Extract currency code if available
                    if hasattr(total.value_currency, 'code') and total.value_currency.code:
                        extracted_data["currency"] = total.value_currency.code
                        logger.info(f"💰 Total: {total.value_currency.code} {total.value_currency.amount} (confidence: {total.confidence})")
                    else:
                        logger.info(f"💰 Total: {total.value_currency.amount} (confidence: {total.confidence})")
                else:
                    logger.warning("⚠️ No total amount found")
                
                # Tax amount
                tax = receipt.fields.get("TotalTax")
                if tax:
                    extracted_data["tax_amount"] = float(tax.value_currency.amount)
                    logger.info(f"🧾 Tax: {tax.value_currency.amount} (confidence: {tax.confidence})")
                else:
                    logger.info("ℹ️ No tax amount found")
                
                # Subtotal
                subtotal = receipt.fields.get("Subtotal")
                if subtotal:
                    extracted_data["subtotal"] = float(subtotal.value_currency.amount)
                    logger.info(f"📊 Subtotal: {subtotal.value_currency.amount} (confidence: {subtotal.confidence})")
                else:
                    logger.info("ℹ️ No subtotal found")

                # Extract line items
                if receipt.fields.get("Items"):
                    items = []
                    items_field = receipt.fields.get("Items")
                    logger.info(f"📝 Found {len(items_field.value_array)} items")
                    
                    for item_idx, item in enumerate(items_field.value_array):
                        logger.info(f"📦 Processing item #{item_idx + 1}")
                        item_data = {}
                        
                        item_description = item.value_object.get("Description")
                        if item_description:
                            item_data["name"] = item_description.value_string
                            logger.info(f"  📝 Description: {item_description.value_string}")
                        
                        item_quantity = item.value_object.get("Quantity")
                        if item_quantity:
                            item_data["quantity"] = item_quantity.value_number
                            logger.info(f"  🔢 Quantity: {item_quantity.value_number}")
                        
                        item_price = item.value_object.get("Price")
                        if item_price:
                            item_data["unit_price"] = float(item_price.value_currency.amount)
                            logger.info(f"  💵 Unit Price: {item_price.value_currency.amount}")
                        
                        item_total_price = item.value_object.get("TotalPrice")
                        if item_total_price:
                            item_data["price"] = float(item_total_price.value_currency.amount)
                            logger.info(f"  💰 Total Price: {item_total_price.value_currency.amount}")
                        
                        items.append(item_data)
                    extracted_data["items"] = items
                else:
                    logger.warning("⚠️ No items found in receipt")

            logger.info(f"🎉 Receipt extraction completed successfully: {extracted_data}")
            return extracted_data

        except Exception as e:
            logger.error(f"❌ Failed to extract receipt data: {str(e)}")
            logger.exception("Full exception details:")
            raise Exception(f"Failed to extract receipt data: {str(e)}")

class AzureOpenAIService:
    def __init__(self):
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")
        
        if not self.endpoint or not self.api_key:
            logger.warning("Azure OpenAI credentials not configured - service will be unavailable")
            self.client = None
            return
        
        try:
            self.client = AzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                api_version="2024-02-15-preview"
            )
            logger.info("Azure OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI client: {e}")
            self.client = None

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
