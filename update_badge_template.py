import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models.badge_template import BadgeTemplate

db = SessionLocal()

# Get the badge template
template = db.query(BadgeTemplate).filter(BadgeTemplate.id == 1).first()

if template:
    # Update the template with corrected HTML
    template.template_content = '''<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Badge</title>
  <style>
    @media print {
      body { margin: 0; padding: 0; }
      @page { size: A4; margin: 0.5in; }
      .badge { page-break-inside: avoid; }
    }
    .badge {
      width: 3.5in;
      height: auto;
      min-height: 5.5in;
      background: linear-gradient(to bottom, #dc2626 0%, #dc2626 65%, white 65%, white 100%);
      position: relative;
      border-radius: 12px;
      overflow: visible;
      font-family: Arial, sans-serif;
      margin: 20px auto;
      box-shadow: 0 4px 8px rgba(0,0,0,0.1);
      -webkit-print-color-adjust: exact;
      color-adjust: exact;
      display: flex;
      flex-direction: column;
    }
    .hole {
      position: absolute;
      top: 10px;
      left: 50%;
      transform: translateX(-50%);
      width: 14px;
      height: 14px;
      background: white;
      border-radius: 50%;
      border: 1px solid rgba(0,0,0,0.1);
      z-index: 10;
    }
    .top-section {
      padding: 30px 20px;
      text-align: center;
      color: white;
      flex: 0 0 65%;
      display: flex;
      flex-direction: column;
      justify-content: center;
      position: relative;
      z-index: 1;
    }
    .avatar {
      position: absolute;
      top: 65%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 60px;
      height: 60px;
      border-radius: 50%;
      border: 4px solid white;
      z-index: 20;
      object-fit: cover;
    }
    .bottom-section {
      background: white;
      padding: 40px 20px 20px 20px;
      flex: 1;
      min-height: 35%;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-sizing: border-box;
      position: relative;
      z-index: 1;
    }
    .participant-info {
      text-align: center;
      margin-top: 10px;
    }
    .contact-section {
      display: flex;
      justify-content: space-between;
      align-items: end;
      margin-top: auto;
    }
  </style>
</head>
<body>
  <div class="badge">
    <div class="hole"></div>
    <div class="top-section">
      <div style="text-align: center; margin-bottom: 10px;">{{logo}}</div>
      <h2 style="font-size: 18px; font-weight: bold; margin: 10px 0 5px 0; text-shadow: 0 2px 4px rgba(0,0,0,0.1);">{{eventTitle}}</h2>
      <p style="font-size: 10px; margin: 0; opacity: 0.9;">{{startDate}} - {{endDate}}</p>
    </div>
    {{participantAvatar}}
    <div class="bottom-section">
      <div class="participant-info">
        <h3 style="font-size: 16px; font-weight: bold; color: #1f2937; margin: 0 0 5px 0;">{{participantName}}</h3>
        <p style="font-size: 11px; color: #6b7280; margin: 0 0 5px 0;">{{participantRole}}</p>
        <p style="font-size: 9px; color: #9ca3af; margin: 0;">{{badgeTagline}}</p>
      </div>
      <div class="contact-section">
        <div style="font-size: 8px; color: #9ca3af; line-height: 1.4; flex: 1;">
          ''' + (template.contact_phone or '+123 456 789') + '''<br/>
          ''' + (template.website_url or 'www.msf.org') + '''
        </div>
        ''' + ('<div style="width: 45px; height: 45px; border: 1px solid #d1d5db; display: flex; align-items: center; justify-content: center; font-size: 7px; color: #6b7280; background: #f9fafb; margin-left: 10px;">QR</div>' if template.enable_qr_code else '') + '''
      </div>
    </div>
  </div>
</body>
</html>'''
    
    db.commit()
    print("✅ Badge template updated successfully!")
    print(f"   Template ID: {template.id}")
    print(f"   Template Name: {template.name}")
    print(f"   Avatar URL: {template.avatar_url}")
    print(f"   Logo URL: {template.logo_url}")
else:
    print("❌ Badge template not found")

db.close()
