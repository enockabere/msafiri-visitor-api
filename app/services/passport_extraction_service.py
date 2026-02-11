"""Passport extraction service using Azure Document Intelligence."""
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PassportExtractionService:
    """Extract data from passport using Azure Document Intelligence prebuilt-idDocument model."""

    def __init__(self):
        self.endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        self.api_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

    async def extract_passport_data(self, image_url: str) -> Dict[str, Any]:
        """
        Extract passport data from an image URL using Azure Document Intelligence.

        Args:
            image_url: URL of the passport image stored in Azure Blob Storage

        Returns:
            Dictionary containing extracted passport fields:
            {
                "full_name": str,
                "given_names": str,
                "surname": str,
                "date_of_birth": str (ISO date),
                "passport_number": str,
                "expiry_date": str (ISO date),
                "nationality": str,
                "gender": str,
                "issue_country": str,
                "confidence_scores": Dict[str, float]
            }
        """
        if not self.endpoint or not self.api_key:
            logger.error("Azure Document Intelligence credentials not configured")
            raise ValueError("Azure Document Intelligence credentials not configured")

        try:
            from azure.ai.formrecognizer import DocumentAnalysisClient
            from azure.core.credentials import AzureKeyCredential

            client = DocumentAnalysisClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.api_key)
            )

            # Use the prebuilt-idDocument model for passport extraction
            poller = client.begin_analyze_document_from_url(
                model_id="prebuilt-idDocument",
                document_url=image_url
            )
            result = poller.result()

            # Extract passport-specific fields
            extracted_data = {
                "full_name": None,
                "given_names": None,
                "surname": None,
                "date_of_birth": None,
                "passport_number": None,
                "expiry_date": None,
                "nationality": None,
                "gender": None,
                "issue_country": None,
                "confidence_scores": {}
            }

            # Process the first document (passport)
            if result.documents:
                doc = result.documents[0]
                fields = doc.fields

                # Map Document Intelligence fields to our schema
                field_mapping = {
                    "FirstName": "given_names",
                    "LastName": "surname",
                    "DateOfBirth": "date_of_birth",
                    "DocumentNumber": "passport_number",
                    "DateOfExpiration": "expiry_date",
                    "Nationality": "nationality",
                    "Sex": "gender",
                    "CountryRegion": "issue_country",
                }

                for di_field, our_field in field_mapping.items():
                    if di_field in fields and fields[di_field]:
                        field_value = fields[di_field]
                        value = field_value.value

                        # Handle date fields
                        if our_field in ["date_of_birth", "expiry_date"]:
                            if value:
                                if isinstance(value, datetime):
                                    value = value.strftime("%Y-%m-%d")
                                elif hasattr(value, 'isoformat'):
                                    value = value.isoformat()[:10]

                        extracted_data[our_field] = value
                        extracted_data["confidence_scores"][our_field] = field_value.confidence

                # Construct full name from given names and surname
                if extracted_data["given_names"] and extracted_data["surname"]:
                    extracted_data["full_name"] = f"{extracted_data['given_names']} {extracted_data['surname']}"
                elif extracted_data["given_names"]:
                    extracted_data["full_name"] = extracted_data["given_names"]
                elif extracted_data["surname"]:
                    extracted_data["full_name"] = extracted_data["surname"]

            logger.info(f"Successfully extracted passport data: {extracted_data['passport_number']}")
            return extracted_data

        except ImportError:
            logger.error("azure-ai-formrecognizer package not installed")
            raise ImportError("azure-ai-formrecognizer package required for passport extraction")
        except Exception as e:
            logger.error(f"Error extracting passport data: {e}")
            raise

    async def extract_passport_data_from_bytes(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Extract passport data from image bytes using Azure Document Intelligence.

        Args:
            image_bytes: Raw bytes of the passport image

        Returns:
            Same as extract_passport_data
        """
        if not self.endpoint or not self.api_key:
            logger.error("Azure Document Intelligence credentials not configured")
            raise ValueError("Azure Document Intelligence credentials not configured")

        try:
            from azure.ai.formrecognizer import DocumentAnalysisClient
            from azure.core.credentials import AzureKeyCredential
            from io import BytesIO

            client = DocumentAnalysisClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.api_key)
            )

            # Use the prebuilt-idDocument model for passport extraction
            poller = client.begin_analyze_document(
                model_id="prebuilt-idDocument",
                document=BytesIO(image_bytes)
            )
            result = poller.result()

            # Extract passport-specific fields (same logic as URL-based extraction)
            extracted_data = {
                "full_name": None,
                "given_names": None,
                "surname": None,
                "date_of_birth": None,
                "passport_number": None,
                "expiry_date": None,
                "nationality": None,
                "gender": None,
                "issue_country": None,
                "confidence_scores": {}
            }

            if result.documents:
                doc = result.documents[0]
                fields = doc.fields

                field_mapping = {
                    "FirstName": "given_names",
                    "LastName": "surname",
                    "DateOfBirth": "date_of_birth",
                    "DocumentNumber": "passport_number",
                    "DateOfExpiration": "expiry_date",
                    "Nationality": "nationality",
                    "Sex": "gender",
                    "CountryRegion": "issue_country",
                }

                for di_field, our_field in field_mapping.items():
                    if di_field in fields and fields[di_field]:
                        field_value = fields[di_field]
                        value = field_value.value

                        if our_field in ["date_of_birth", "expiry_date"]:
                            if value:
                                if isinstance(value, datetime):
                                    value = value.strftime("%Y-%m-%d")
                                elif hasattr(value, 'isoformat'):
                                    value = value.isoformat()[:10]

                        extracted_data[our_field] = value
                        extracted_data["confidence_scores"][our_field] = field_value.confidence

                if extracted_data["given_names"] and extracted_data["surname"]:
                    extracted_data["full_name"] = f"{extracted_data['given_names']} {extracted_data['surname']}"
                elif extracted_data["given_names"]:
                    extracted_data["full_name"] = extracted_data["given_names"]
                elif extracted_data["surname"]:
                    extracted_data["full_name"] = extracted_data["surname"]

            logger.info(f"Successfully extracted passport data from bytes: {extracted_data['passport_number']}")
            return extracted_data

        except ImportError:
            logger.error("azure-ai-formrecognizer package not installed")
            raise ImportError("azure-ai-formrecognizer package required for passport extraction")
        except Exception as e:
            logger.error(f"Error extracting passport data from bytes: {e}")
            raise


# Singleton instance
passport_extraction_service = PassportExtractionService()
