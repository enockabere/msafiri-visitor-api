"""
Revert to justify-content: space-between which worked before
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("SELECT id, name, template_content FROM badge_templates"))
    templates = result.fetchall()
    
    for template in templates:
        template_id, name, content = template
        
        if not content:
            continue
        
        # Change justify-content back to space-between
        if "justify-content: flex-start" in content:
            content = content.replace(
                "justify-content: flex-start",
                "justify-content: space-between"
            )
            
            # Remove margin-left: auto from QR since space-between handles it
            content = content.replace("margin-left: auto;", "")
            
            # Remove margin-right: auto from logo since space-between handles it
            content = content.replace("margin-right: auto;", "")
            
            # Remove flex: 0 0 auto from logo
            content = content.replace("flex: 0 0 auto;", "")
            
            conn.execute(
                text("UPDATE badge_templates SET template_content = :content WHERE id = :id"),
                {"content": content, "id": template_id}
            )
            conn.commit()
            print(f"✅ Reverted {name} to space-between")
        else:
            print(f"✓ {name} already using space-between")

print("\n✅ Done!")
