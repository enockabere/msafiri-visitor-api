"""
Add flex: 0 0 auto to logo-container to prevent it from taking all space
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
        
        # Add flex: 0 0 auto to logo-container if not present
        if "flex: 0 0 auto" not in content and ".logo-container {" in content:
            content = content.replace(
                "text-align: left;",
                "text-align: left;\n      flex: 0 0 auto;"
            )
            
            conn.execute(
                text("UPDATE badge_templates SET template_content = :content WHERE id = :id"),
                {"content": content, "id": template_id}
            )
            conn.commit()
            print(f"✅ Added flex to {name}")
        else:
            print(f"✓ {name} already has flex")

print("\n✅ Done!")
