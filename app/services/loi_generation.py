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
# Use API_BASE_URL from environment for QR code generation
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def replace_template_variables(template_html: str, data: Dict[str, Any]) -> str:
    """
    Replace template variables with actual participant data and make them bold.
    Also auto-format emails, phones, and URLs.

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

    # Format standalone URLs in address section only (not in src/href attributes)
    result = format_address_links(result)
    
    # Add inline styles to all <a> tags to ensure they are blue and underlined
    result = add_link_styles(result)

    return result


def add_link_styles(html: str) -> str:
    """
    Add inline styles to all <a> tags to ensure they are blue and underlined in PDF.
    """
    import re
    
    def add_style(match):
        tag = match.group(0)
        if 'style="' in tag:
            if 'color:' not in tag:
                tag = tag.replace('style="', 'style="color: #1a73e8; ')
            if 'text-decoration:' not in tag:
                tag = tag.replace('style="', 'style="text-decoration: underline; ')
        else:
            tag = tag.replace('>', ' style="color: #1a73e8; text-decoration: underline;">', 1)
        return tag
    
    html = re.sub(r'<a\s+[^>]*>', add_style, html)
    
    return html


def format_address_links(html: str) -> str:
    """
    Format standalone URLs in the address section to be clickable links.
    Only formats URLs that are not already in HTML tags.
    """
    import re
    
    lines = html.split('\n')
    result_lines = []
    
    for line in lines:
        if 'href="' in line or 'src="' in line or '</a>' in line:
            result_lines.append(line)
            continue
        
        url_pattern = r'(https?://[^\s<>"]+)'
        
        def replace_url(match):
            url = match.group(1)
            return f'<a href="{url}" style="color: #1a73e8; text-decoration: underline;" target="_blank">{url}</a>'
        
        line = re.sub(url_pattern, replace_url, line)
        result_lines.append(line)
    
    return '\n'.join(result_lines)


def auto_format_contact_info(html: str) -> str:
    """
    Auto-detect and format emails, phone numbers, and URLs with proper styling and links.
    Only formats plain text, not content already in HTML tags or attributes.
    """
    import re
    
    # Format email addresses (not already in <a> tags or attributes)
    # Negative lookbehind to avoid emails in href, src, or already linked
    email_pattern = r'(?<!href=")(?<!src=")(?<!mailto:)(?<!</a>)(?<!=")\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b(?![^<]*>)(?![^<]*</a>)'
    
    def format_email(match):
        email = match.group(1)
        # Check if this email is inside an HTML tag
        return f'<a href="mailto:{email}" class="email">{email}</a>'
    
    html = re.sub(email_pattern, format_email, html)
    
    # Format phone numbers (not in attributes)
    # Only format if it's plain text, not inside HTML tags
    phone_pattern = r'(?<!href=")(?<!src=")(?<!=")(?<!\d)(\+?\d{1,4}[\s-]?\(?\d{1,4}\)?[\s-]?\d{1,4}[\s-]?\d{1,4}[\s-]?\d{1,9})(?!\d)(?![^<]*>)'
    
    def format_phone(match):
        phone = match.group(1)
        # Only format if it looks like a phone number (has enough digits)
        if len(re.sub(r'[^\d]', '', phone)) >= 9:
            return f'<a href="tel:{phone}" class="phone">{phone}</a>'
        return phone
    
    html = re.sub(phone_pattern, format_phone, html)
    
    # Format URLs (not already in href, src, or <a> tags)
    # Much more restrictive - only format standalone URLs in plain text
    url_pattern = r'(?<!href=")(?<!src=")(?<!</a>)(?<!=")\b(https?://[^\s<>"]+|www\.[^\s<>"]+)\b(?![^<]*>)(?![^<]*</a>)(?![^<]*")'
    
    def format_url(match):
        url = match.group(1)
        # Don't format if it looks like it's part of an HTML attribute
        href = url if url.startswith('http') else f'http://{url}'
        return f'<a href="{href}" class="website" target="_blank">{url}</a>'
    
    html = re.sub(url_pattern, format_url, html)
    
    return html


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
                margin: 1.2cm 1.2cm 1cm 1.2cm;  /* Reduced top margin further */
            }
            body {
                font-family: 'Arial', 'Helvetica', sans-serif;
                line-height: 1.4;
                color: #333;
                font-size: 11px;
                margin: 0;
                padding: 0;
            }
            h1, h2, h3 {
                color: #dc2626;
                margin: 6px 0;  /* Further reduced margins */
            }
            p {
                margin: 5px 0;  /* Further reduced paragraph margins */
            }
            .letterhead {
                display: grid;
                grid-template-columns: auto 1fr auto;
                align-items: start;
                gap: 10px;
                margin-bottom: 10px;  /* Reduced from 15px */
            }
            .logo img {
                height: 80px;
                max-width: 150px;
            }
            .qr {
                display: flex;
                justify-content: center;
                align-items: flex-start;
            }
            .qr img {
                width: 55px;  /* Increased from 50px to 55px */
                height: 55px;
            }
            .address {
                text-align: left;
                font-size: 10px;
                line-height: 1.3;
                justify-self: end;
                max-width: 250px;
                min-width: 200px;
            }
            .address p, .address a {
                margin: 2px 0;
                display: block;
            }
            .address .org {
                font-weight: bold;
                font-size: 11px;
            }
            .address .tel, .address .phone {
                margin-top: 4px;
                color: #059669;
                font-weight: 500;
            }
            .address .email {
                color: #1a73e8;
                text-decoration: none;
                font-weight: 500;
            }
            .address .email:hover {
                text-decoration: underline;
            }
            .address a {
                color: #1a73e8;
                text-decoration: none;
                font-weight: 500;
            }
            .address a:hover {
                text-decoration: underline;
            }
            .address .website {
                color: #1a73e8 !important;
                text-decoration: underline !important;
                font-weight: 500;
            }
            /* General link styling */
            a {
                color: #1a73e8 !important;
                text-decoration: underline !important;
            }
            /* Make variables bold */
            .variable {
                font-weight: bold;
                color: #000;
            }
            /* Signature section styling */
            .signature-section {
                margin-top: 25px;  /* Reduced from 30px */
                page-break-inside: avoid;
            }
            .signature-footer {
                margin-top: 4px;  /* Reduced from 8px */
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

        # Construct API URL for QR code
        public_url = f"{API_BASE_URL}/api/v1/loi/events/{event_id}/participant/{participant_id}/generate"

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
                qr_html = f'<img src="{qr_code_base64}" style="width: 55px; height: 55px;" alt="QR Code" />'
                personalized_html = personalized_html.replace('{{qr_code}}', qr_html)
        else:
            # Replace QR code placeholders if they exist in template
            if qr_code_base64:
                qr_html = f'<img src="{qr_code_base64}" style="width: 55px; height: 55px;" alt="QR Code" />'
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
