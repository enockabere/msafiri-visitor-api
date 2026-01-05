"""
Proof of Accommodation PDF Generation Service

This service generates personalized proof of accommodation documents
from HTML templates and uploads them to Azure Blob Storage.
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import uuid
from io import BytesIO

logger = logging.getLogger(__name__)

# Cloudinary configuration
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")


def replace_template_variables(template_html: str, data: Dict[str, Any]) -> str:
    """
    Replace template variables with actual data.

    Template variables format: {{variableName}}

    Args:
        template_html: HTML template with variables
        data: Dictionary containing variable values

    Returns:
        HTML with variables replaced
    """
    result = template_html

    # Define all supported variables
    variables = {
        'participantName': data.get('participant_name', ''),
        'hotelName': data.get('hotel_name', ''),
        'hotelAddress': data.get('hotel_address', ''),
        'checkInDate': data.get('check_in_date', ''),
        'checkOutDate': data.get('check_out_date', ''),
        'roomNumber': data.get('room_number', 'TBD'),
        'roomType': data.get('room_type', ''),
        'eventName': data.get('event_name', ''),
        'eventDates': data.get('event_dates', ''),
        'confirmationNumber': data.get('confirmation_number', ''),
    }

    # Replace each variable
    for key, value in variables.items():
        placeholder = f'{{{{{key}}}}}'
        result = result.replace(placeholder, str(value))

    return result


def generate_confirmation_number(participant_id: int, event_id: int) -> str:
    """
    Generate a unique confirmation number for the booking.

    Format: MSF-EVENT{eventId}-PART{participantId}-{random}
    Example: MSF-EVENT123-PART456-A7B9
    """
    random_part = str(uuid.uuid4())[:4].upper()
    return f"MSF-EVENT{event_id}-PART{participant_id}-{random_part}"


async def html_to_pdf_bytes(html_content: str) -> BytesIO:
    """
    Convert HTML to PDF bytes using WeasyPrint.

    Args:
        html_content: HTML string to convert

    Returns:
        BytesIO containing PDF data
    """
    try:
        from weasyprint import HTML, CSS

        # Add CSS for better PDF formatting
        css_string = """
            @page {
                size: A4;
                margin: 2cm;
            }
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }
            h1, h2, h3 {
                color: #dc2626;
            }
            table {
                width: 100%;
                border-collapse: collapse;
            }
            .protected-url {
                display: none !important;
            }
        """

        css = CSS(string=css_string)
        pdf_bytes = HTML(string=html_content).write_pdf(stylesheets=[css])

        return BytesIO(pdf_bytes)

    except ImportError:
        logger.error("WeasyPrint not installed. Install with: pip install weasyprint")
        raise Exception("PDF generation library not available")
    except Exception as e:
        logger.error(f"Error converting HTML to PDF: {str(e)}")
        raise


async def upload_pdf_to_cloudinary(pdf_bytes: BytesIO, filename: str) -> str:
    """
    Upload PDF to Cloudinary and return public URL.

    Args:
        pdf_bytes: BytesIO containing PDF data
        filename: Name for the file

    Returns:
        Public URL of uploaded PDF
    """
    try:
        import cloudinary
        import cloudinary.uploader
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
            api_key=os.getenv("CLOUDINARY_API_KEY"),
            api_secret=os.getenv("CLOUDINARY_API_SECRET")
        )
        
        if not os.getenv("CLOUDINARY_CLOUD_NAME"):
            raise Exception("Cloudinary not configured")

        # Reset pointer to beginning
        pdf_bytes.seek(0)
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            pdf_bytes,
            public_id=filename,  # Keep full filename with .pdf extension
            folder="msafiri-documents/poa",
            resource_type="raw",
            format="pdf",  # Explicitly set format as PDF
            use_filename=False,  # Don't use original filename
            unique_filename=False,  # Use our custom filename
            overwrite=True
        )

        return result["secure_url"]

    except ImportError:
        raise Exception("Cloudinary SDK not installed")
    except Exception as e:
        logger.error(f"Error uploading PDF to Cloudinary: {str(e)}")
        raise


async def generate_proof_of_accommodation(
    participant_id: int,
    event_id: int,
    template_html: str,
    hotel_name: str,
    hotel_address: str,
    check_in_date: str,
    check_out_date: str,
    room_type: str,
    event_name: str,
    event_dates: str,
    participant_name: str,
    room_number: Optional[str] = None
) -> str:
    """
    Generate complete proof of accommodation PDF and upload to Azure.

    Args:
        participant_id: ID of the participant
        event_id: ID of the event
        template_html: HTML template from vendor hotel
        hotel_name: Name of the hotel
        hotel_address: Full address of the hotel
        check_in_date: Check-in date (formatted string)
        check_out_date: Check-out date (formatted string)
        room_type: Type of room (Single/Double)
        event_name: Name of the event
        event_dates: Event date range (formatted string)
        participant_name: Full name of participant
        room_number: Room number (optional, default TBD)

    Returns:
        Public URL of the generated PDF
    """
    try:
        logger.info(f"Generating proof of accommodation for participant {participant_id}, event {event_id}")

        # Generate confirmation number
        confirmation_number = generate_confirmation_number(participant_id, event_id)

        # Prepare data for template
        template_data = {
            'participant_name': participant_name,
            'hotel_name': hotel_name,
            'hotel_address': hotel_address,
            'check_in_date': check_in_date,
            'check_out_date': check_out_date,
            'room_number': room_number or 'TBD',
            'room_type': room_type,
            'event_name': event_name,
            'event_dates': event_dates,
            'confirmation_number': confirmation_number,
        }

        # Replace variables in template
        personalized_html = replace_template_variables(template_html, template_data)

        # Convert to PDF
        pdf_bytes = await html_to_pdf_bytes(personalized_html)

        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"proof-accommodation-{event_id}-{participant_id}-{timestamp}.pdf"

        # Upload to Cloudinary
        pdf_url = await upload_pdf_to_cloudinary(pdf_bytes, filename)

        logger.info(f"✅ Proof of accommodation generated: {pdf_url}")

        return pdf_url

    except Exception as e:
        logger.error(f"❌ Failed to generate proof of accommodation: {str(e)}")
        raise Exception(f"Failed to generate proof of accommodation: {str(e)}")


def validate_template_variables(template_html: str) -> Dict[str, bool]:
    """
    Check which template variables are used in the template.

    Returns:
        Dictionary with variable names as keys and boolean values indicating presence
    """
    variables = [
        'participantName',
        'hotelName',
        'hotelAddress',
        'checkInDate',
        'checkOutDate',
        'roomNumber',
        'roomType',
        'eventName',
        'eventDates',
        'confirmationNumber',
    ]

    result = {}
    for var in variables:
        placeholder = f'{{{{{var}}}}}'
        result[var] = placeholder in template_html

    return result
