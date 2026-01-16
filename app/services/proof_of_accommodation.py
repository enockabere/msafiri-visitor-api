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

    # Define all supported variables (excluding image URLs which are handled separately)
    variables = {
        'participantName': data.get('participant_name', ''),
        'hotelName': data.get('hotel_name', ''),
        'hotelAddress': data.get('hotel_address', ''),
        'checkInDate': data.get('check_in_date', ''),
        'checkOutDate': data.get('check_out_date', ''),
        'roomType': data.get('room_type', ''),
        'eventName': data.get('event_name', ''),
        'eventDates': data.get('event_dates', ''),
        'confirmationNumber': data.get('confirmation_number', ''),
        'tenantName': data.get('tenant_name', ''),
        # Note: qrCode, hotelLogo, signature are handled separately as images
    }

    # Replace each variable
    for key, value in variables.items():
        placeholder = f'{{{{{key}}}}}'
        result = result.replace(placeholder, str(value))

    return result


def generate_poa_slug(participant_id: int, event_id: int) -> str:
    """
    Generate a secure, unique slug for public POA access.
    """
    import hashlib
    unique_string = f"{participant_id}-{event_id}-{uuid.uuid4()}-{datetime.utcnow().timestamp()}"
    hash_object = hashlib.sha256(unique_string.encode())
    hash_hex = hash_object.hexdigest()
    return hash_hex[:32]


def generate_qr_code(url: str) -> str:
    """
    Generate QR code image as base64 string.
    """
    try:
        import qrcode
        import base64
        from io import BytesIO

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )

        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        return f"data:image/png;base64,{img_base64}"

    except ImportError:
        logger.error("qrcode library not installed")
        return ""
    except Exception as e:
        logger.error(f"Error generating QR code: {str(e)}")
        return ""


def generate_confirmation_number(participant_id: int, event_id: int, allocation_id: int) -> str:
    """
    Generate a unique confirmation number for the booking.

    Format: MSF-EVENT{eventId}-PART{participantId}-{allocationId}
    Example: MSF-EVENT12-PART22-567
    """
    return f"MSF-EVENT{event_id}-PART{participant_id}-{allocation_id}"


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
                margin: 1.5cm;
            }
            body {
                font-family: Arial, sans-serif;
                line-height: 1.4;
                color: #333;
                font-size: 11pt;
            }
            h1 {
                color: #dc2626;
                font-size: 18pt;
                margin: 10px 0;
            }
            h2 {
                color: #333;
                font-size: 14pt;
                margin: 8px 0;
            }
            h3 {
                color: #dc2626;
                font-size: 12pt;
                margin: 8px 0;
            }
            p {
                margin: 6px 0;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 10px 0;
            }
            td {
                padding: 4px 0;
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
    allocation_id: int,
    template_html: str,
    hotel_name: str,
    hotel_address: str,
    check_in_date: str,
    check_out_date: str,
    room_type: str,
    event_name: str,
    event_dates: str,
    participant_name: str,
    tenant_name: str = "Organization",
    logo_url: Optional[str] = None,
    signature_url: Optional[str] = None,
    enable_qr_code: bool = True
) -> tuple[str, str]:
    """
    Generate complete proof of accommodation PDF and upload to Azure.

    Returns:
        Tuple of (pdf_url, poa_slug)
    """
    try:
        logger.info(f"Generating proof of accommodation for participant {participant_id}, event {event_id}")

        # Generate confirmation number
        confirmation_number = generate_confirmation_number(participant_id, event_id, allocation_id)
        
        # Generate QR code if enabled
        qr_code_base64 = ""
        if enable_qr_code:
            poa_slug = generate_poa_slug(participant_id, event_id)
            api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
            public_url = f"{api_url}/api/v1/poa/{poa_slug}"
            qr_code_base64 = generate_qr_code(public_url)

        # Prepare data for template
        template_data = {
            'participant_name': participant_name,
            'hotel_name': hotel_name,
            'hotel_address': hotel_address,
            'check_in_date': check_in_date,
            'check_out_date': check_out_date,
            'room_type': room_type,
            'event_name': event_name,
            'event_dates': event_dates,
            'confirmation_number': confirmation_number,
            'tenant_name': tenant_name,
            'qr_code': qr_code_base64,
            'logo_url': logo_url or '',
            'signature_url': signature_url or '',
        }

        # Replace variables in template
        personalized_html = replace_template_variables(template_html, template_data)
        
        # Handle QR code insertion if enabled and QR code was generated
        if enable_qr_code and qr_code_base64 and '{{qrCode}}' in personalized_html:
            # Replace {{qrCode}} with proper HTML img tag (100x100px like LOI)
            qr_img_tag = f'<img src="{qr_code_base64}" style="width: 100px; height: 100px;" alt="QR Code" />'
            personalized_html = personalized_html.replace('{{qrCode}}', qr_img_tag)
        elif '{{qrCode}}' in personalized_html:
            # Remove QR code placeholder if no QR code generated
            personalized_html = personalized_html.replace('{{qrCode}}', '')
            
        # Handle logo URL - convert to HTML img tag
        if logo_url and '{{hotelLogo}}' in personalized_html:
            logo_img_tag = f'<img src="{logo_url}" style="max-width: 200px; height: auto;" alt="Hotel Logo" />'
            personalized_html = personalized_html.replace('{{hotelLogo}}', logo_img_tag)
        elif '{{hotelLogo}}' in personalized_html:
            personalized_html = personalized_html.replace('{{hotelLogo}}', '')
            
        # Handle signature URL - convert to HTML img tag  
        if signature_url and '{{signature}}' in personalized_html:
            signature_img_tag = f'<img src="{signature_url}" style="max-width: 150px; height: auto;" alt="Signature" />'
            personalized_html = personalized_html.replace('{{signature}}', signature_img_tag)
        elif '{{signature}}' in personalized_html:
            personalized_html = personalized_html.replace('{{signature}}', '')

        # Convert to PDF
        pdf_bytes = await html_to_pdf_bytes(personalized_html)

        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"proof-accommodation-{event_id}-{participant_id}-{timestamp}.pdf"

        # Upload to Cloudinary
        pdf_url = await upload_pdf_to_cloudinary(pdf_bytes, filename)

        logger.info(f"✅ Proof of accommodation generated: {pdf_url}")

        return pdf_url, poa_slug

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
        'roomType',
        'eventName',
        'eventDates',
        'confirmationNumber',
        'tenantName',
    ]

    result = {}
    for var in variables:
        placeholder = f'{{{{{var}}}}}'
        result[var] = placeholder in template_html

    return result
