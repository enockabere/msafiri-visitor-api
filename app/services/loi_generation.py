"""
Letter of Invitation (LOI) Generation Service

Generates personalized Letter of Invitation documents with QR codes
for event participants using their passport data.
"""

import os
import logging
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
import uuid
from io import BytesIO
import base64

logger = logging.getLogger(__name__)

# Azure configuration
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_LOI_CONTAINER = os.getenv("AZURE_LOI_DOCUMENTS_CONTAINER", "loi-documents")
# Use FRONTEND_URL from environment, fallback to localhost for development
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000/portal")


def replace_template_variables(template_html: str, data: Dict[str, Any]) -> str:
    """
    Replace template variables with actual participant data and make them bold.

    Template variables format: {{variableName}}
    """
    import re
    result = template_html
    
    # Find template variables in the template
    template_vars = re.findall(r'\{\{\s*([^}]+)\s*\}\}', template_html)

    # Define all supported variables with multiple naming conventions
    variables = {
        # Participant data
        'participantName': data.get('participant_name', ''),
        'participant_name': data.get('participant_name', ''),
        'passportNumber': data.get('passport_number', ''),
        'passport_number': data.get('passport_number', ''),
        'nationality': data.get('nationality', ''),
        'dateOfBirth': data.get('date_of_birth', ''),
        'date_of_birth': data.get('date_of_birth', ''),
        'passportIssueDate': data.get('passport_issue_date', ''),
        'passport_issue_date': data.get('passport_issue_date', ''),
        'passportExpiryDate': data.get('passport_expiry_date', ''),
        'passport_expiry_date': data.get('passport_expiry_date', ''),
        # Event data
        'eventName': data.get('event_name', ''),
        'event_name': data.get('event_name', ''),
        'eventDates': data.get('event_dates', ''),
        'event_dates': data.get('event_dates', ''),
        'eventLocation': data.get('event_location', ''),
        'event_location': data.get('event_location', ''),
        'event_start_date': data.get('event_start_date', ''),
        'event_end_date': data.get('event_end_date', ''),
        'accommodation_details': data.get('accommodation_details', ''),
        # Organization data
        'organizationName': data.get('organization_name', 'MSF'),
        'organization_name': data.get('organization_name', 'MSF'),
        'organizer_name': data.get('organizer_name', ''),
        'organizer_title': data.get('organizer_title', ''),
        'currentDate': datetime.now().strftime('%B %d, %Y'),
        'current_date': datetime.now().strftime('%B %d, %Y'),
    }

    # Replace each variable with bold formatting
    for key, value in variables.items():
        if value:  # Only replace if value is not empty
            bold_value = f'<span class="variable">{value}</span>'
            patterns = [
                f'{{{{{key}}}}}',  # {{variable}}
                f'{{{{ {key} }}}}',  # {{ variable }}
            ]
            for pattern in patterns:
                if pattern.replace('{{', '').replace('}}', '').strip() in template_vars or key in template_vars:
                    result = result.replace(pattern, bold_value)

    # Also try regex replacement for whitespace variations
    for key, value in variables.items():
        if value:  # Only replace if value is not empty
            bold_value = f'<span class="variable">{value}</span>'
            pattern = f'{{{{\s*{re.escape(key)}\s*}}}}'
            matches = re.findall(pattern, result, re.IGNORECASE)
            if matches:
                result = re.sub(pattern, bold_value, result, flags=re.IGNORECASE)

    return result


def generate_loi_slug(participant_id: int, event_id: int) -> str:
    """
    Generate a secure, unique slug for public LOI access.

    Format: Base64(SHA256(participant_id + event_id + random))
    Example: a7b9c3d4e5f6...
    """
    unique_string = f"{participant_id}-{event_id}-{uuid.uuid4()}-{datetime.utcnow().timestamp()}"
    hash_object = hashlib.sha256(unique_string.encode())
    hash_hex = hash_object.hexdigest()

    # Take first 32 characters for reasonable URL length
    return hash_hex[:32]


def generate_qr_code(url: str) -> str:
    """
    Generate QR code image as base64 string.

    Args:
        url: Public URL to encode in QR code

    Returns:
        Base64 encoded QR code image (PNG)
    """
    try:
        import qrcode
        from qrcode.image.pure import PyPNGImage

        # Create QR code instance with smaller size for mobile
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=6,  # Reduced from 10 to 6
            border=2,    # Reduced from 4 to 2
        )

        qr.add_data(url)
        qr.make(fit=True)

        # Create image with smaller dimensions
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        # Encode to base64
        img_base64 = base64.b64encode(buffer.read()).decode('utf-8')

        return f"data:image/png;base64,{img_base64}"

    except ImportError:
        logger.error("qrcode library not installed")
        return ""
    except Exception as e:
        logger.error(f"Error generating QR code: {str(e)}")
        return ""


async def html_to_pdf_bytes(html_content: str) -> BytesIO:
    """
    Convert HTML to PDF bytes using WeasyPrint with mobile-optimized settings.
    """
    try:
        from weasyprint import HTML, CSS

        css_string = """
            @page {
                size: A4;
                margin: 1.5cm 1.2cm;  /* Reduced margins for mobile */
            }
            body {
                font-family: 'Arial', 'Helvetica', sans-serif;
                line-height: 1.4;  /* Reduced line height */
                color: #333;
                font-size: 11px;  /* Reduced base font size */
            }
            h1, h2, h3 {
                color: #dc2626;
                margin: 8px 0;  /* Reduced margins */
            }
            p {
                margin: 6px 0;  /* Reduced paragraph margins */
            }
            .letterhead {
                display: grid;
                grid-template-columns: auto 1fr auto;
                align-items: start;  /* Changed from center to start */
                gap: 10px;
                margin-bottom: 15px;  /* Reduced margin */
            }
            .logo img {
                height: 80px;  /* Reduced from 120px */
                max-width: 150px;  /* Reduced from 200px */
            }
            .qr {
                display: flex;
                justify-content: center;
                align-items: flex-start;
            }
            .qr img {
                width: 50px;  /* Fixed small size */
                height: 50px;
            }
            .address {
                text-align: left;
                font-size: 10px;  /* Reduced font size */
                line-height: 1.3;
                justify-self: end;
                max-width: 180px;  /* Constrain width */
            }
            .address p, .address a {
                margin: 2px 0;  /* Reduced margins */
                display: block;
            }
            .address .org {
                font-weight: bold;
                font-size: 11px;
            }
            .address .tel {
                margin-top: 4px;
            }
            .address a {
                color: #1a73e8;
                text-decoration: none;
            }
            /* Make variables bold */
            .variable {
                font-weight: bold;
                color: #000;
            }
            /* Signature section styling */
            .signature-section {
                margin-top: 30px;
                page-break-inside: avoid;
            }
            .signature-footer {
                margin-top: 8px;
                font-size: 10px;
                line-height: 1.3;
                clear: both;
            }
            /* Ensure single page */
            .content {
                page-break-inside: avoid;
            }
        """

        css = CSS(string=css_string)
        pdf_bytes = HTML(string=html_content).write_pdf(stylesheets=[css])

        return BytesIO(pdf_bytes)

    except ImportError:
        logger.error("WeasyPrint not installed")
        raise Exception("PDF generation library not available")
    except Exception as e:
        logger.error(f"Error converting HTML to PDF: {str(e)}")
        raise


async def upload_pdf_to_cloudinary(pdf_bytes: BytesIO, filename: str) -> str:
    """
    Upload LOI PDF to Cloudinary and return public URL.
    """
    try:
        import cloudinary
        import cloudinary.uploader
        from dotenv import load_dotenv
        
        load_dotenv()
        
        cloudinary.config(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
            api_key=os.getenv("CLOUDINARY_API_KEY"),
            api_secret=os.getenv("CLOUDINARY_API_SECRET")
        )
        
        if not os.getenv("CLOUDINARY_CLOUD_NAME"):
            raise Exception("Cloudinary not configured")

        pdf_bytes.seek(0)
        
        result = cloudinary.uploader.upload(
            pdf_bytes,
            public_id=filename,
            folder="msafiri-documents/loi",
            resource_type="raw",
            format="pdf",
            use_filename=False,
            unique_filename=False,
            overwrite=True
        )

        return result["secure_url"]

    except ImportError:
        raise Exception("Cloudinary SDK not installed")
    except Exception as e:
        logger.error(f"Error uploading PDF to Cloudinary: {str(e)}")
        raise


async def generate_loi_document(
    participant_id: int,
    event_id: int,
    template_html: str,
    participant_name: str,
    passport_number: Optional[str] = None,
    nationality: Optional[str] = None,
    date_of_birth: Optional[str] = None,
    passport_issue_date: Optional[str] = None,
    passport_expiry_date: Optional[str] = None,
    event_name: str = "",
    event_dates: str = "",
    event_location: str = "",
    organization_name: str = "MSF"
) -> tuple[str, str]:
    """
    Generate complete Letter of Invitation PDF with QR code.

    Args:
        participant_id: ID of the participant
        event_id: ID of the event
        template_html: HTML template content
        participant_name: Full name of participant
        passport_number: Passport number from uploaded document
        nationality: Participant's nationality
        date_of_birth: Date of birth
        passport_issue_date: Passport issue date
        passport_expiry_date: Passport expiry date
        event_name: Name of the event
        event_dates: Event date range
        event_location: Event location
        organization_name: Organization name (default: MSF)

    Returns:
        Tuple of (pdf_url, loi_slug)
    """
    try:
        logger.info(f"Generating LOI for participant {participant_id}, event {event_id}")

        # Generate unique slug for public access
        loi_slug = generate_loi_slug(participant_id, event_id)

        # Construct public URL
        public_url = f"{FRONTEND_URL}/public/loi/{loi_slug}"

        # Generate QR code
        qr_code_base64 = generate_qr_code(public_url)

        # Prepare data for template
        template_data = {
            'participant_name': participant_name,
            'passport_number': passport_number or 'N/A',
            'nationality': nationality or 'N/A',
            'date_of_birth': date_of_birth or 'N/A',
            'passport_issue_date': passport_issue_date or 'N/A',
            'passport_expiry_date': passport_expiry_date or 'N/A',
            'event_name': event_name,
            'event_dates': event_dates,
            'event_start_date': event_dates.split(' - ')[0] if ' - ' in event_dates else event_dates,
            'event_end_date': event_dates.split(' - ')[1] if ' - ' in event_dates else event_dates,
            'event_location': event_location,
            'accommodation_details': 'MSF approved accommodation',
            'organization_name': organization_name,
            'organizer_name': 'Isaac Kimani',
            'organizer_title': 'Admin Transit',
        }

        # Replace variables in template
        personalized_html = replace_template_variables(template_html, template_data)
        
        # Ensure QR code placeholder is handled with smaller size
        if '{{qrCode}}' not in personalized_html and '{{qr_code}}' not in personalized_html:
            # Add QR code section in letterhead if not already present
            if qr_code_base64 and '<div class="letterhead">' in personalized_html:
                qr_html = f'<img src="{qr_code_base64}" style="width: 50px; height: 50px;" alt="QR Code" />'
                personalized_html = personalized_html.replace('{{qr_code}}', qr_html)
        else:
            # Replace QR code placeholders if they exist in template
            if qr_code_base64:
                qr_html = f'<img src="{qr_code_base64}" style="width: 50px; height: 50px;" alt="QR Code" />'
                personalized_html = personalized_html.replace('{{qrCode}}', qr_html)
                personalized_html = personalized_html.replace('{{qr_code}}', qr_html)
            else:
                personalized_html = personalized_html.replace('{{qrCode}}', '')
                personalized_html = personalized_html.replace('{{qr_code}}', '')

        # Convert to PDF
        pdf_bytes = await html_to_pdf_bytes(personalized_html)

        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"loi-{event_id}-{participant_id}-{timestamp}.pdf"

        # Upload to Cloudinary
        pdf_url = await upload_pdf_to_cloudinary(pdf_bytes, filename)



        return pdf_url, loi_slug

    except Exception as e:
        logger.error(f"❌ Failed to generate LOI: {str(e)}")
        raise Exception(f"Failed to generate LOI: {str(e)}")
