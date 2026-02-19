"""
Update badge templates to fix QR code styling:
1. Change justify-content from space-between to flex-start
2. Add margin-right: auto to logo-container
3. Change QR inner background from gradient to white
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

def update_templates():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, name, template_content FROM badge_templates"))
        templates = result.fetchall()
        
        print(f"Found {len(templates)} badge templates")
        
        for template in templates:
            template_id, name, content = template
            
            if not content:
                print(f"  Skipping {name} (no content)")
                continue
            
            updated = False
            new_content = content
            
            # Fix 1: Change justify-content from space-between to flex-start
            if "justify-content: space-between" in new_content:
                new_content = new_content.replace("justify-content: space-between", "justify-content: flex-start")
                updated = True
                print(f"  Fixed justify-content in {name}")
            
            # Fix 2: Add margin-right: auto to logo-container if not present
            if "margin-right: auto" not in new_content and ".logo-container {" in new_content:
                new_content = new_content.replace(
                    "margin-bottom: 0;",
                    "margin-bottom: 0;\n      margin-right: auto;"
                )
                updated = True
                print(f"  Added margin-right: auto to logo in {name}")
            
            # Fix 3: Change QR inner background from gradient to white
            if "background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%)" in new_content:
                new_content = new_content.replace(
                    "background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%)",
                    "background: white"
                )
                updated = True
                print(f"  Removed grey gradient from QR in {name}")
            
            if updated:
                conn.execute(
                    text("UPDATE badge_templates SET template_content = :content WHERE id = :id"),
                    {"content": new_content, "id": template_id}
                )
                conn.commit()
                print(f"  ✅ Updated template {name}")
            else:
                print(f"  ✓ Template {name} is already up to date")

if __name__ == "__main__":
    print("Updating badge templates...")
    update_templates()
    print("\n✅ Done!")
