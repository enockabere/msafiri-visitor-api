"""
Check current badge template CSS
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("SELECT id, name, template_content FROM badge_templates LIMIT 1"))
    template = result.fetchone()
    
    if template:
        print(f"Template: {template.name}")
        print("\n=== QR Container CSS ===")
        content = template.template_content
        
        # Find .qr-top-right section
        start = content.find(".qr-top-right {")
        if start != -1:
            end = content.find("}", start)
            print(content[start:end+1])
        
        print("\n=== Top Section CSS ===")
        start = content.find(".top-section {")
        if start != -1:
            end = content.find("}", start)
            print(content[start:end+1])
            
        print("\n=== Logo Container CSS ===")
        start = content.find(".logo-container {")
        if start != -1:
            end = content.find("}", start)
            print(content[start:end+1])
