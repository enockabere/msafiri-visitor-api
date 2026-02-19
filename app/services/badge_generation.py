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
        elif key in ['qr_code', 'qrCode', 'QR'] and value and (value.startswith('http') or value.startswith('data:image')):
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

        # Badge-specific CSS for proper sizing
        css_string = """
            @page {
                size: 4in 6in;
                margin: 0;
            }
            body {
                margin: 0;
                padding: 0;
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

        # Generate QR code as base64 data URI (same as LOI)
        import qrcode
        from io import BytesIO
        import base64
        
        base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
        badge_view_url = f"{base_url}/api/v1/events/{event_id}/participant/{participant_id}/badge/generate"
        
        # Generate QR code with same settings as LOI
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=6,
            border=2,
        )
        qr.add_data(badge_view_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 data URI
        buffered = BytesIO()
        qr_img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode()
        qr_code_data_uri = f"data:image/png;base64,{qr_base64}"
        
        logger.info(f"QR code generated as base64 data URI")

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
            'qr_code': qr_code_data_uri,
            'qrCode': qr_code_data_uri,
            'QR': qr_code_data_uri,
            'logo': logo_url if logo_url else '',
            'avatar': avatar_url if avatar_url else '',
        }

        logger.info(f"Template data prepared with QR code data URI")

        # Use original badge design matching ParticipantBadge.tsx
        personalized_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Badge</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    width: 4in;
                    height: 6in;
                    margin: 0;
                    padding: 0;
                    background: white;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                }}
                .badge-wrapper {{
                    width: 100%;
                    height: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: #f3f4f6;
                }}
                .badge-container {{
                    width: 320px;
                    height: 480px;
                    background: white;
                    border-radius: 24px;
                    overflow: hidden;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.15);
                }}
                .side-dots {{
                    width: 32px;
                    height: 100%;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-around;
                    align-items: center;
                    padding: 32px 0;
                    z-index: 10;
                }}
                .dot {{
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    background: #d1d5db;
                }}
                .top-section {{
                    background: linear-gradient(135deg, #dc2626 0%, #b91c1c 50%, #991b1b 100%);
                    padding: 48px 32px 64px;
                    min-height: 280px;
                    text-align: center;
                    color: white;
                }}
                .event-logo {{
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 12px;
                    margin-bottom: 24px;
                }}
                .logo-icon {{
                    width: 40px;
                    height: 40px;
                    background: #2563eb;
                    border-radius: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 20px;
                    font-weight: bold;
                }}
                .logo-text {{
                    font-size: 18px;
                    font-weight: bold;
                    letter-spacing: 2px;
                }}
                .event-title {{
                    font-size: 32px;
                    font-weight: 900;
                    margin-bottom: 12px;
                    letter-spacing: -0.5px;
                    line-height: 1.1;
                }}
                .event-location, .event-date {{
                    font-size: 14px;
                    color: #d1d5db;
                    margin: 8px 0;
                }}
                .qr-container {{
                    display: flex;
                    justify-content: center;
                    margin-top: 32px;
                }}
                .qr-box {{
                    background: white;
                    padding: 12px;
                    border-radius: 12px;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                }}
                .qr-box img {{
                    width: 80px;
                    height: 80px;
                    display: block;
                }}
                .bottom-section {{
                    background: white;
                    padding: 24px 32px;
                    min-height: 200px;
                    text-align: center;
                }}
                .participant-name {{
                    font-size: 28px;
                    font-weight: 900;
                    color: #111827;
                    margin-bottom: 12px;
                    letter-spacing: -0.5px;
                    line-height: 1.2;
                }}
                .participant-email {{
                    font-size: 11px;
                    color: #6b7280;
                    font-weight: 500;
                    word-break: break-all;
                    padding: 0 8px;
                }}
                .bottom-bar {{
                    background: #2563eb;
                    color: white;
                    padding: 16px;
                    text-align: center;
                    margin-top: 32px;
                    border-radius: 0 0 24px 24px;
                }}
                .bottom-bar p {{
                    font-size: 12px;
                    font-weight: bold;
                    text-transform: uppercase;
                    letter-spacing: 3px;
                }}
            </style>
        </head>
        <body>
            <div class="badge-wrapper">
                <div class="badge-container">
                    <div class="top-section">
                        <div class="event-logo">
                            <div class="logo-icon">★</div>
                            <span class="logo-text">EVENT</span>
                        </div>
                        <h1 class="event-title">{event_name}</h1>
                        <div class="event-location">📍 {tagline or 'Event Location'}</div>
                        <div class="event-date">📅 {event_dates}</div>
                        <div class="qr-container">
                            <div class="qr-box">
                                <img src="{qr_code_data_uri}" alt="QR Code" />
                            </div>
                        </div>
                    </div>
                    <div class="bottom-section">
                        <h2 class="participant-name">{display_name}</h2>
                        <p class="participant-email">{participant_role}</p>
                        <div class="bottom-bar">
                            <p>Participant</p>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        logger.info("Using original badge design matching ParticipantBadge.tsx")

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
