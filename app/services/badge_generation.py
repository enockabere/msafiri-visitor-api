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
        'qrCode': data.get('qr_code', '') or data.get('qrCode', ''),
        'qr_code': data.get('qr_code', '') or data.get('qrCode', ''),
        'QR': data.get('qr_code', '') or data.get('QR', ''),
    }

    # Replace each variable with both {{variable}} and {{{variable}}} formats
    for key, value in variables.items():
        # Handle image variables by creating img tags
        if key == 'logo' and value and value.startswith('http'):
            img_tag = f'<img src="{value}" alt="Logo" style="max-width:150px;max-height:100px" />'
            result = result.replace(f'{{{{{key}}}}}', img_tag)
            result = result.replace(f'{{{{{{{key}}}}}}}', img_tag)
        elif key in ['qr_code', 'qrCode', 'QR'] and value and value.startswith('http'):
            img_tag = f'<img src="{value}" alt="QR Code" style="width:74px;height:74px;margin:3px;background:white;display:block;object-fit:contain;border:0.5px solid #d1d5db" />'
            result = result.replace(f'{{{{{key}}}}}', img_tag)
            result = result.replace(f'{{{{{{{key}}}}}}}', img_tag)
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
    avatar_url: str = "",
    enable_qr_code: bool = True
) -> str:
    """
    Generate complete badge PDF and upload to Cloudinary.
    """
    try:
        logger.info(f"Generating badge for participant {participant_id}, event {event_id}")

        # Generate QR code and save as temporary file for WeasyPrint
        import qrcode
        from io import BytesIO
        import tempfile
        import os
        
        base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
        badge_view_url = f"{base_url}/api/v1/events/{event_id}/participant/{participant_id}/badge/generate"
        
        # Generate QR code image
        qr = qrcode.QRCode(version=1, box_size=10, border=1)
        qr.add_data(badge_view_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to temporary file
        temp_qr_path = f"/tmp/qr_badge_{event_id}_{participant_id}.png"
        qr_img.save(temp_qr_path)
        
        logger.info(f"QR code saved to temp file: {temp_qr_path}")

        # Prepare data for template
        display_name = badge_name if badge_name else participant_name

        template_data = {
            'participant_name': display_name,
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
            'qr_code': temp_qr_path,
            'qrCode': temp_qr_path,
            'QR': temp_qr_path,
            'logo': logo_url if logo_url else '',
            'avatar': avatar_url if avatar_url else '',
        }

        logger.info(f"Template data prepared with QR code file path")

        # Replace variables in template
        personalized_html = replace_template_variables(template_html, template_data)

        # Ensure QR section is visible
        import re
        personalized_html = re.sub(
            r'(\.qr-top-right\s*\{[^}]*display\s*:\s*)none',
            r'\1flex',
            personalized_html
        )
        logger.info("Ensuring .qr-top-right is visible")

        # Replace static "QR" text with actual QR code image (handles nested divs)
        import re
        qr_img_tag = f'<img src="file://{temp_qr_path}" alt="QR Code" style="width:74px;height:74px;margin:3px;background:white;display:block;object-fit:contain;border:0.5px solid #d1d5db" />'
        
        # Replace <div class="qr-inner">QR</div> or similar patterns
        personalized_html = re.sub(
            r'<div class="qr-inner">QR</div>',
            f'<div class="qr-inner">{qr_img_tag}</div>',
            personalized_html
        )
        
        # Also handle simple >QR< pattern as fallback
        personalized_html = personalized_html.replace('>QR<', f'>{qr_img_tag}<')
        
        logger.info("Replaced QR placeholder with QR code image")
        
        print(f"\n=== FINAL HTML CHECK ===")
        print(f"Final HTML contains QR file path: {temp_qr_path in personalized_html}")
        if temp_qr_path in personalized_html:
            # Find and print context around QR code
            idx = personalized_html.find(temp_qr_path)
            context_start = max(0, idx - 100)
            context_end = min(len(personalized_html), idx + 200)
            print(f"QR code context: ...{personalized_html[context_start:context_end]}...")

        # Convert to PDF
        pdf_bytes = await html_to_pdf_bytes(personalized_html)
        
        # Clean up temp QR file
        try:
            os.remove(temp_qr_path)
        except:
            pass

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
