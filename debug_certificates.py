#!/usr/bin/env python3
"""
Debug certificate setup and fix any issues.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'msafiri_db')
DB_USER = os.getenv('POSTGRES_USER', 'msafiri_user')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'password@1234')

def debug_certificates():
    """Debug and fix certificate setup."""
    
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
        print("=== DEBUGGING CERTIFICATE SETUP ===\n")
        
        # 1. Check event and participant
        print("1. Checking event and participant...")
        cursor.execute("""
            SELECT e.id, e.title, e.tenant_id, t.name as tenant_name
            FROM events e
            JOIN tenants t ON e.tenant_id = t.id
            WHERE e.id = 7
        """)
        event_data = cursor.fetchone()
        if event_data:
            event_id, event_title, tenant_id, tenant_name = event_data
            print(f"   ✓ Event: {event_title} (ID: {event_id}, Tenant: {tenant_name}, Tenant ID: {tenant_id})")
        else:
            print("   ✗ Event 7 not found!")
            return
            
        cursor.execute("""
            SELECT id, full_name, email
            FROM event_participants 
            WHERE id = 8 AND event_id = 7
        """)
        participant = cursor.fetchone()
        if participant:
            print(f"   ✓ Participant: {participant[1]} (ID: {participant[0]}, Email: {participant[2]})")
        else:
            print("   ✗ Participant 8 not found in event 7!")
            return
        
        # 2. Check certificate templates
        print("\n2. Checking certificate templates...")
        cursor.execute("SELECT id, name, tenant_id FROM certificate_templates WHERE tenant_id = %s", (tenant_id,))
        templates = cursor.fetchall()
        if templates:
            for template in templates:
                print(f"   ✓ Template: {template[1]} (ID: {template[0]}, Tenant ID: {template[2]})")
        else:
            print("   ✗ No certificate templates found for this tenant!")
            return
            
        # 3. Check event certificates
        print("\n3. Checking event certificates...")
        cursor.execute("""
            SELECT ec.id, ec.event_id, ec.certificate_template_id, ct.name
            FROM event_certificates ec
            JOIN certificate_templates ct ON ec.certificate_template_id = ct.id
            WHERE ec.event_id = 7
        """)
        event_certs = cursor.fetchall()
        if event_certs:
            for cert in event_certs:
                print(f"   ✓ Event Certificate: {cert[3]} (ID: {cert[0]}, Template ID: {cert[2]})")
        else:
            print("   ✗ No event certificates found for event 7!")
            
        # 4. Check participant certificates
        print("\n4. Checking participant certificates...")
        cursor.execute("""
            SELECT pc.id, pc.participant_id, pc.event_certificate_id, pc.certificate_url, pc.issued_at
            FROM participant_certificates pc
            WHERE pc.participant_id = 8
        """)
        participant_certs = cursor.fetchall()
        if participant_certs:
            for cert in participant_certs:
                print(f"   ✓ Participant Certificate: ID {cert[0]}, Event Cert ID: {cert[2]}, URL: {cert[3]}")
        else:
            print("   ✗ No participant certificates found for participant 8!")
            
        # 5. Fix the issue - create proper certificate assignment
        print("\n5. Creating certificate assignment...")
        
        # Get or create certificate template
        cursor.execute("""
            SELECT id FROM certificate_templates 
            WHERE tenant_id = %s 
            ORDER BY created_at DESC 
            LIMIT 1
        """, (tenant_id,))
        template_result = cursor.fetchone()
        
        if not template_result:
            # Create a default template
            cursor.execute("""
                INSERT INTO certificate_templates (name, description, template_content, tenant_id)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (
                "MSF Kenya Conference Certificate",
                "Certificate for MSF Kenya Humanitarian Technical Conference",
                "Certificate template content",
                tenant_id
            ))
            template_id = cursor.fetchone()[0]
            print(f"   ✓ Created certificate template with ID: {template_id}")
        else:
            template_id = template_result[0]
            print(f"   ✓ Using existing certificate template with ID: {template_id}")
        
        # Create or update event certificate
        cursor.execute("""
            INSERT INTO event_certificates (event_id, certificate_template_id)
            VALUES (%s, %s)
            ON CONFLICT (event_id, certificate_template_id) 
            DO NOTHING
            RETURNING id
        """, (event_id, template_id))
        result = cursor.fetchone()
        if result:
            event_cert_id = result[0]
        else:
            # Get existing ID
            cursor.execute("""
                SELECT id FROM event_certificates 
                WHERE event_id = %s AND certificate_template_id = %s
            """, (event_id, template_id))
            event_cert_id = cursor.fetchone()[0]
        print(f"   ✓ Event certificate link ID: {event_cert_id}")
        
        # Create participant certificate with proper URL
        certificate_url = f"https://certificates.msafiri.com/event-{event_id}-participant-{participant[0]}.pdf"
        
        cursor.execute("""
            INSERT INTO participant_certificates (participant_id, event_certificate_id, certificate_url, issued_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (participant_id, event_certificate_id)
            DO UPDATE SET 
                certificate_url = EXCLUDED.certificate_url,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """, (participant[0], event_cert_id, certificate_url))
        
        cert_id = cursor.fetchone()[0]
        print(f"   ✓ Participant certificate created/updated with ID: {cert_id}")
        print(f"   ✓ Certificate URL: {certificate_url}")
        
        # 6. Verify the fix
        print("\n6. Verifying the fix...")
        cursor.execute("""
            SELECT 
                ep.full_name as participant_name,
                COALESCE(ep.certificate_name, ep.full_name) as certificate_name,
                e.title as event_name,
                pc.certificate_url,
                pc.issued_at as certificate_issued_at
            FROM event_participants ep
            JOIN events e ON ep.event_id = e.id
            LEFT JOIN participant_certificates pc ON ep.id = pc.participant_id
            LEFT JOIN event_certificates ec ON pc.event_certificate_id = ec.id AND ec.event_id = e.id
            WHERE ep.email = %s AND e.id = %s
        """, (participant[2], event_id))
        
        result = cursor.fetchone()
        if result and result[3]:  # certificate_url exists
            print(f"   ✓ SUCCESS! Certificate found for {result[0]}")
            print(f"   ✓ Certificate Name: {result[1]}")
            print(f"   ✓ Certificate URL: {result[3]}")
        else:
            print("   ✗ Certificate still not found after fix!")
            
        print("\n=== CERTIFICATE DEBUG COMPLETE ===")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    debug_certificates()