#!/usr/bin/env python3
"""
Set up certificate for the MSF Kenya Humanitarian Technical Conference event.
This creates the necessary records to link the certificate to the event and participant.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters from production .env
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'msafiri_db')
DB_USER = os.getenv('POSTGRES_USER', 'msafiri_user')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'password@1234')

def setup_event_certificate():
    """Set up certificate for the MSF Kenya event."""
    
    # Connect to database
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    try:
        print("Setting up certificate for MSF Kenya Humanitarian Technical Conference...")
        
        # Get event and tenant info first
        cursor.execute("""
            SELECT e.id, e.title, e.tenant_id, t.name as tenant_name
            FROM events e
            JOIN tenants t ON e.tenant_id = t.id
            WHERE e.id = 7
        """)
        event_data = cursor.fetchone()
        
        if not event_data:
            print("[ERROR] Event with ID 7 not found")
            return
            
        event_id, event_title, tenant_id, tenant_name = event_data
        print(f"[OK] Found event: {event_title} (Tenant: {tenant_name})")
        
        # 1. Create a default certificate template with tenant_id
        cursor.execute("""
            INSERT INTO certificate_templates (name, description, template_content, tenant_id)
            VALUES ('Default Certificate', 'Default event certificate template', 'Default certificate content', %s)
            ON CONFLICT DO NOTHING
            RETURNING id;
        """, (tenant_id,))
        
        result = cursor.fetchone()
        if result:
            template_id = result[0]
            print(f"[OK] Created certificate template with ID: {template_id}")
        else:
            # Template already exists, get its ID
            cursor.execute("SELECT id FROM certificate_templates WHERE name = 'Default Certificate' AND tenant_id = %s LIMIT 1;", (tenant_id,))
            result = cursor.fetchone()
            if result:
                template_id = result[0]
                print(f"[OK] Using existing certificate template with ID: {template_id}")
            else:
                print("[ERROR] No matching certificate template found")
                return
        
        # 2. Link the certificate template to event 7 (MSF Kenya Humanitarian Technical Conference)
        cursor.execute("""
            INSERT INTO event_certificates (event_id, certificate_template_id, is_active)
            VALUES (7, %s, TRUE)
            ON CONFLICT (event_id, certificate_template_id) DO NOTHING
            RETURNING id;
        """, (template_id,))
        
        result = cursor.fetchone()
        if result:
            event_cert_id = result[0]
            print(f"[OK] Created event certificate link with ID: {event_cert_id}")
        else:
            # Link already exists, get its ID
            cursor.execute("SELECT id FROM event_certificates WHERE event_id = 7 AND certificate_template_id = %s LIMIT 1;", (template_id,))
            event_cert_id = cursor.fetchone()[0]
            print(f"[OK] Using existing event certificate link with ID: {event_cert_id}")
        
        # 3. Create a certificate for participant 8 (Enock Abere)
        # First check if participant exists
        cursor.execute("SELECT id, full_name FROM event_participants WHERE id = 8 AND event_id = 7;")
        participant = cursor.fetchone()
        
        if not participant:
            print("[ERROR] Participant 8 not found in event 7")
            return
        
        print(f"[OK] Found participant: {participant[1]} (ID: {participant[0]})")
        
        # Create the participant certificate record
        certificate_url = "https://example.com/certificates/msf-kenya-conference-enock-abere.pdf"
        
        cursor.execute("""
            INSERT INTO participant_certificates (participant_id, event_certificate_id, certificate_url, issued_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (participant_id, event_certificate_id) 
            DO UPDATE SET certificate_url = EXCLUDED.certificate_url, updated_at = CURRENT_TIMESTAMP
            RETURNING id;
        """, (participant[0], event_cert_id, certificate_url))
        
        cert_id = cursor.fetchone()[0]
        print(f"[OK] Created/updated participant certificate with ID: {cert_id}")
        print(f"[OK] Certificate URL: {certificate_url}")
        
        print("\n[SUCCESS] Certificate setup completed successfully!")
        print("The certificate should now be visible in the mobile app.")
        
    except Exception as e:
        print("[ERROR] Error setting up certificate:", e)
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    setup_event_certificate()