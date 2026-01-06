"""
Badge Generation Service

Generates personalized badges for event participants using badge templates.
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import uuid
from io import BytesIO

logger = logging.getLogger(__name__)


def replace_template_variables(template_html: str, data: Dict[str, Any]) -> str:
    """
    Replace template variables with actual data.
    """
    result = template_html

    # Define all supported variables with both formats
    variables = {
        # New format
        'participantName': data.get('participant_name', ''),
        'badgeName': data.get('badge_name', ''),
        'eventName': data.get('event_name', ''),
        'eventTitle': data.get('event_name', ''),  # Alternative name
        'eventDates': data.get('event_dates', ''),
        'startDate': data.get('start_date', ''),
        'endDate': data.get('end_date', ''),
        'eventLocation': data.get('event_location', ''),
        'organizationName': data.get('organization_name', 'MSF'),
        'participantRole': data.get('participant_role', 'Participant'),
        'badgeTagline': data.get('tagline', ''),
        'tagline': data.get('tagline', ''),
        'currentDate': datetime.now().strftime('%B %d, %Y'),
        'logo': data.get('logo', ''),
        'qrCode': data.get('qr_code', ''),
    }

    # Replace each variable with both {{variable}} and {{{variable}}} formats
    for key, value in variables.items():
        # Handle QR code as image (simplified CSS to avoid escaping)
        if key == 'qr_code' and value and value.startswith('http'):
            img_tag = f'<img src="{value}" alt="QR Code" style="width:100px;height:100px" />'
            result = result.replace(f'{{{{{key}}}}}', img_tag)
            result = result.replace(f'{{{{{{{key}}}}}}}', img_tag)
        # Handle logo as image (simplified CSS)
        elif key == 'logo' and value and value.startswith('http'):
            img_tag = f'<img src="{value}" alt="Logo" style="max-width:150px;max-height:100px" />'
            result = result.replace(f'{{{{{key}}}}}', img_tag)
            result = result.replace(f'{{{{{{{key}}}}}}}', img_tag)
        # Handle avatar as image (simplified CSS)
        elif key == 'avatar' and value and value.startswith('http'):
            img_tag = f'<img src="{value}" alt="Avatar" style="max-width:100px;max-height:100px;border-radius:50%" />'
            result = result.replace(f'{{{{{key}}}}}', img_tag)
            result = result.replace(f'{{{{{{{key}}}}}}}', img_tag)
        else:
            # Regular text replacement
            result = result.replace(f'{{{{{key}}}}}', str(value))
            result = result.replace(f'{{{{{{{key}}}}}}}', str(value))

    return result


async def html_to_pdf_bytes(html_content: str) -> BytesIO:
    """
    Convert HTML to PDF bytes using WeasyPrint.
    """
    try:
        from weasyprint import HTML, CSS

        # Minimal CSS that doesn't override template styles
        css_string = """
            @page {
                size: A4 portrait;
                margin: 0.5cm;
            }
            /* Preserve original template styles */
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
    Upload PDF to Cloudinary and return public URL.
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
            folder="msafiri-documents/badges",
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


async def generate_badge(
    participant_id: int,
    event_id: int,
    template_html: str,
    participant_name: str,
    badge_name: str,
    event_name: str,
    event_dates: str,
    tagline: str = "",
    organization_name: str = "MSF",
    start_date: str = "",
    end_date: str = "",
    participant_role: str = "Participant",
    logo_url: str = "",
    avatar_url: str = ""
) -> str:
    """
    Generate complete badge PDF and upload to Cloudinary.
    """
    try:
        logger.info(f"Generating badge for participant {participant_id}, event {event_id}")

        # Generate QR code URL that points to the badge itself
        base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
        badge_view_url = f"{base_url}/api/v1/events/{event_id}/participant/{participant_id}/badge/generate"
        qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={badge_view_url}"

        # Prepare data for template - replace image placeholders with actual URLs
        template_data = {
            'participant_name': participant_name,
            'badge_name': badge_name,
            'event_name': event_name,
            'event_title': event_name,
            'event_dates': event_dates,
            'start_date': start_date,
            'end_date': end_date,
            'organization_name': organization_name,
            'participant_role': participant_role,
            'tagline': tagline,
            'badge_tagline': tagline,
            'qr_code': qr_code_url,
            'logo': logo_url if logo_url else '',
            'avatar': avatar_url if avatar_url else '',
        }

        logger.info(f"Template data: {template_data}")

        # Replace variables in template first
        personalized_html = replace_template_variables(template_html, template_data)
        
        # Then replace any remaining text placeholders with images (avoid HTML escaping)
        if logo_url and 'Logo' in personalized_html:
            # Use simple replacement without quotes to avoid escaping
            logo_img = f'<img src="{logo_url}" alt="Logo" style="max-width:150px;max-height:100px" />'
            personalized_html = personalized_html.replace('Logo', logo_img)
        
        # Add QR code - check for common QR placeholders
        qr_img = f'<img src="{qr_code_url}" alt="QR Code" style="width:100px;height:100px" />'
        
        # Replace various QR code placeholders
        personalized_html = personalized_html.replace('{{qrCode}}', qr_img)
        personalized_html = personalized_html.replace('{{qr_code}}', qr_img)
        personalized_html = personalized_html.replace('QR Code', qr_img)
        personalized_html = personalized_html.replace('QRCode', qr_img)
        
        # If no QR placeholder found, add QR to bottom right
        if 'QR' not in personalized_html and qr_code_url:
            # Add QR code to the end of body
            qr_div = f'<div style="position:absolute;bottom:10px;right:10px">{qr_img}</div>'
            personalized_html = personalized_html.replace('</body>', f'{qr_div}</body>')
        
        logger.info(f"Personalized HTML preview: {personalized_html[:500]}...")

        # Convert to PDF
        pdf_bytes = await html_to_pdf_bytes(personalized_html)

        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"badge-{event_id}-{participant_id}-{timestamp}.pdf"

        # Upload to Cloudinary
        pdf_url = await upload_pdf_to_cloudinary(pdf_bytes, filename)

        logger.info(f"✅ Badge generated: {pdf_url}")

        return pdf_url

    except Exception as e:
        logger.error(f"❌ Failed to generate badge: {str(e)}")
        raise Exception(f"Failed to generate badge: {str(e)}")