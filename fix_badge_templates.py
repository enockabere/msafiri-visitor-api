"""
Fix badge templates by removing position: absolute from QR code containers
This CSS breaks base64 image rendering in WeasyPrint
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in environment")
    sys.exit(1)

engine = create_engine(DATABASE_URL)

def fix_templates():
    with engine.connect() as conn:
        # Get all badge templates
        result = conn.execute(text("SELECT id, name, template_content FROM badge_templates"))
        templates = result.fetchall()
        
        print(f"Found {len(templates)} badge templates")
        
        for template in templates:
            template_id, name, content = template
            
            if not content:
                print(f"  Skipping {name} (no content)")
                continue
            
            # Check if template has position: absolute
            if "position: absolute" in content or "position:absolute" in content:
                print(f"\n  Fixing template: {name} (ID: {template_id})")
                
                # Remove position: absolute and related positioning
                fixed_content = content.replace("position: absolute;", "")
                fixed_content = fixed_content.replace("position:absolute;", "")
                fixed_content = fixed_content.replace("position: absolute", "")
                fixed_content = fixed_content.replace("position:absolute", "")
                
                # Also remove top, left, right, bottom that were used with absolute positioning
                # But be careful not to break other styles
                
                # Update the template
                conn.execute(
                    text("UPDATE badge_templates SET template_content = :content WHERE id = :id"),
                    {"content": fixed_content, "id": template_id}
                )
                conn.commit()
                
                print(f"    ✅ Fixed template {name}")
            else:
                print(f"  ✓ Template {name} is OK (no absolute positioning)")

if __name__ == "__main__":
    print("Fixing badge templates...")
    fix_templates()
    print("\n✅ Done!")
