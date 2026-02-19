"""
Comprehensive fix for QR code positioning in badge templates
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import re

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

def fix_qr_container(content):
    """Fix .qr-top-right CSS"""
    # Find the .qr-top-right block
    pattern = r'\.qr-top-right\s*\{[^}]+\}'
    
    def replace_qr(match):
        # Extract size from existing CSS
        size_match = re.search(r'width:\s*(\d+)px', match.group(0))
        width = size_match.group(1) if size_match else '80'
        
        height_match = re.search(r'height:\s*(\d+)px', match.group(0))
        height = height_match.group(1) if height_match else '90'
        
        padding_match = re.search(r'padding:\s*(\d+)px', match.group(0))
        padding = padding_match.group(1) if padding_match else '4'
        
        # Return fixed CSS
        return f'''.qr-top-right {{
      position: relative;
      width: {width}px;
      height: {height}px;
      padding: {padding}px;
      background: white;
      border-radius: 4px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-left: auto;
      flex-shrink: 0;
    }}'''
    
    return re.sub(pattern, replace_qr, content, flags=re.DOTALL)

def fix_qr_inner(content):
    """Fix .qr-inner CSS to remove grey gradient"""
    pattern = r'\.qr-top-right\s+\.qr-inner\s*\{[^}]+\}'
    
    def replace_inner(match):
        # Extract size
        size_match = re.search(r'width:\s*(\d+)px', match.group(0))
        width = size_match.group(1) if size_match else '80'
        
        height_match = re.search(r'height:\s*(\d+)px', match.group(0))
        height = height_match.group(1) if height_match else '80'
        
        font_match = re.search(r'font-size:\s*(\d+)px', match.group(0))
        font_size = font_match.group(1) if font_match else '12'
        
        return f'''.qr-top-right .qr-inner {{
      width: {width}px;
      height: {height}px;
      background: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: {font_size}px;
      color: #6b7280;
      font-weight: 500;
    }}'''
    
    return re.sub(pattern, replace_inner, content, flags=re.DOTALL)

with engine.connect() as conn:
    result = conn.execute(text("SELECT id, name, template_content FROM badge_templates"))
    templates = result.fetchall()
    
    print(f"Fixing {len(templates)} templates...")
    
    for template in templates:
        template_id, name, content = template
        
        if not content:
            continue
        
        original = content
        content = fix_qr_container(content)
        content = fix_qr_inner(content)
        
        if content != original:
            conn.execute(
                text("UPDATE badge_templates SET template_content = :content WHERE id = :id"),
                {"content": content, "id": template_id}
            )
            conn.commit()
            print(f"✅ Fixed {name}")
        else:
            print(f"✓ {name} already correct")

print("\n✅ Done!")
