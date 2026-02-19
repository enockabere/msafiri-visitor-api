"""
Certificate Generation Service

Generates personalized certificates for event participants using certificate templates.
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

    # Define all supported variables
    variables = {
        'participantName': data.get('participant_name', ''),
        'certificateName': data.get('certificate_name', ''),
        'eventName': data.get('event_name', ''),
        'eventDates': data.get('event_dates', ''),
        'eventLocation': data.get('event_location', ''),
        'organizationName': data.get('organization_name', 'MSF'),
        'currentDate': datetime.now().strftime('%B %d, %Y'),
        'issueDate': data.get('issue_date', datetime.now().strftime('%B %d, %Y')),
    }

    # Replace each variable
    for key, value in variables.items():
        placeholder = f'{{{{{key}}}}}'
        result = result.replace(placeholder, str(value))

    return result


async def html_to_pdf_bytes(html_content: str) -> BytesIO:
    """
    Convert HTML to PDF bytes using WeasyPrint.
    """
    try:
        from weasyprint import HTML, CSS

        css_string = """
            @page {
                size: A4 landscape;
                margin: 0;
            }
            body {
                font-family: 'Arial', 'Helvetica', sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
            }
            h1, h2, h3 {
                color: #dc2626;
            }
            /* Ensure content fits on one page */
            * {
                box-sizing: border-box;
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
            folder="msafiri-documents/certificates",
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


async def generate_certificate(
    participant_id: int,
    event_id: int,
    template_html: str,
    participant_name: str,
    certificate_name: str,
    event_name: str,
    event_dates: str,
    event_location: str,
    organization_name: str = "MSF"
) -> str:
    """
    Generate complete certificate PDF and upload to Cloudinary.
    """
    try:
        logger.info(f"Generating certificate for participant {participant_id}, event {event_id}")

        # Prepare data for template
        template_data = {
            'participant_name': participant_name,
            'certificate_name': certificate_name,
            'event_name': event_name,
            'event_dates': event_dates,
            'event_location': event_location,
            'organization_name': organization_name,
            'issue_date': datetime.now().strftime('%B %d, %Y'),
        }

        # Replace variables in template
        personalized_html = replace_template_variables(template_html, template_data)

        # Convert to PDF
        pdf_bytes = await html_to_pdf_bytes(personalized_html)

        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"certificate-{event_id}-{participant_id}-{timestamp}.pdf"

        # Upload to Cloudinary
        pdf_url = await upload_pdf_to_cloudinary(pdf_bytes, filename)

        logger.info(f"✅ Certificate generated: {pdf_url}")

        return pdf_url

    except Exception as e:
        logger.error(f"❌ Failed to generate certificate: {str(e)}")
        raise Exception(f"Failed to generate certificate: {str(e)}")
