import sys
sys.stdout.reconfigure(encoding='utf-8')

# This script directly inserts default fields into the database
# Run this from the msafiri-visitor-api directory

from app.db.database import get_db
from app.models.form_field import FormField
from sqlalchemy.orm import Session
import json

# Event ID to initialize
EVENT_ID = 1  # Change this to your event ID

# All default form fields
default_fields = [
    # Personal Information Section (101-111)
    {"field_name": "firstName", "field_label": "First Name", "field_type": "text", "is_required": True, "order_index": 101, "section": "personal", "is_protected": True},
    {"field_name": "lastName", "field_label": "Last Name", "field_type": "text", "is_required": True, "order_index": 102, "section": "personal", "is_protected": True},
    {"field_name": "oc", "field_label": "What is your OC?", "field_type": "select", "field_options": json.dumps(["OCA", "OCB", "OCBA", "OCG", "OCP", "WACA"]), "is_required": True, "order_index": 103, "section": "personal", "is_protected": True},
    {"field_name": "contractStatus", "field_label": "Contract Status", "field_type": "select", "field_options": json.dumps(["On contract", "Between contracts"]), "is_required": True, "order_index": 104, "section": "personal", "is_protected": True},
    {"field_name": "contractType", "field_label": "Type of Contract", "field_type": "select", "field_options": json.dumps(["HQ", "IMS", "LRS", "Other"]), "is_required": True, "order_index": 105, "section": "personal"},
    {"field_name": "genderIdentity", "field_label": "Gender Identity", "field_type": "select", "field_options": json.dumps(["Man", "Woman", "Non-binary", "Prefer to self-describe", "Prefer not to disclose"]), "is_required": True, "order_index": 106, "section": "personal", "is_protected": True},
    {"field_name": "sex", "field_label": "Sex", "field_type": "select", "field_options": json.dumps(["Female", "Male", "Other"]), "is_required": True, "order_index": 107, "section": "personal"},
    {"field_name": "pronouns", "field_label": "Pronouns", "field_type": "select", "field_options": json.dumps(["He / him", "She / her", "They / Them", "Other"]), "is_required": True, "order_index": 108, "section": "personal"},
    {"field_name": "currentPosition", "field_label": "Current (or most recent) Position", "field_type": "text", "is_required": True, "order_index": 109, "section": "personal"},
    {"field_name": "countryOfWork", "field_label": "Country of Work", "field_type": "select", "field_options": json.dumps(["Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Argentina", "Armenia", "Australia", "Austria", "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan", "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria", "Burkina Faso", "Burundi", "Cambodia", "Cameroon", "Canada", "Cape Verde", "Central African Republic", "Chad", "Chile", "China", "Colombia", "Comoros", "Congo", "Democratic Republic of the Congo", "Costa Rica", "Croatia", "Cuba", "Cyprus", "Czech Republic", "Denmark", "Djibouti", "Dominica", "Dominican Republic", "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini", "Ethiopia", "Fiji", "Finland", "France", "Gabon", "Gambia", "Georgia", "Germany", "Ghana", "Greece", "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana", "Haiti", "Honduras", "Hungary", "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy", "Jamaica", "Japan", "Jordan", "Kazakhstan", "Kenya", "Kiribati", "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg", "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", "Mauritania", "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia", "Montenegro", "Morocco", "Mozambique", "Myanmar", "Namibia", "Nauru", "Nepal", "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria", "North Korea", "North Macedonia", "Norway", "Oman", "Pakistan", "Palau", "Palestine", "Panama", "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland", "Portugal", "Qatar", "Romania", "Russia", "Rwanda", "Saint Kitts and Nevis", "Saint Lucia", "Saint Vincent and the Grenadines", "Samoa", "San Marino", "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore", "Slovakia", "Slovenia", "Solomon Islands", "Somalia", "South Africa", "South Korea", "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname", "Sweden", "Switzerland", "Syria", "Taiwan", "Tajikistan", "Tanzania", "Thailand", "Timor-Leste", "Togo", "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan", "Tuvalu", "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom", "United States", "Uruguay", "Uzbekistan", "Vanuatu", "Vatican City", "Venezuela", "Vietnam", "Yemen", "Zambia", "Zimbabwe"]), "is_required": False, "order_index": 110, "section": "personal"},
    {"field_name": "projectOfWork", "field_label": "Project of Work", "field_type": "text", "is_required": False, "order_index": 111, "section": "personal"},

    # Contact Details Section (201-206)
    {"field_name": "personalEmail", "field_label": "Personal/Tembo Email Address", "field_type": "email", "is_required": True, "order_index": 201, "section": "contact", "is_protected": True},
    {"field_name": "msfEmail", "field_label": "MSF Email Address", "field_type": "email", "is_required": False, "order_index": 202, "section": "contact"},
    {"field_name": "hrcoEmail", "field_label": "HRCO Email Address", "field_type": "email", "is_required": False, "order_index": 203, "section": "contact"},
    {"field_name": "careerManagerEmail", "field_label": "Career Manager Email Address", "field_type": "email", "is_required": False, "order_index": 204, "section": "contact"},
    {"field_name": "lineManagerEmail", "field_label": "Line Manager Email Address", "field_type": "email", "is_required": False, "order_index": 205, "section": "contact"},
    {"field_name": "phoneNumber", "field_label": "Phone Number", "field_type": "text", "is_required": True, "order_index": 206, "section": "contact", "is_protected": True},

    # Travel & Accommodation Section (301-306)
    {"field_name": "travellingInternationally", "field_label": "Will you be travelling internationally for this event?", "field_type": "select", "field_options": json.dumps(["Yes", "No"]), "is_required": True, "order_index": 301, "section": "travel"},
    {"field_name": "travellingFromCountry", "field_label": "Which country will you be travelling from?", "field_type": "text", "is_required": False, "order_index": 302, "section": "travel"},
    {"field_name": "accommodationType", "field_label": "Accommodation Type", "field_type": "select", "field_options": json.dumps(["Staying at accommodation", "Travelling daily"]), "is_required": True, "order_index": 303, "section": "travel"},
    {"field_name": "dietaryRequirements", "field_label": "Dietary Requirements", "field_type": "textarea", "is_required": False, "order_index": 304, "section": "travel"},
    {"field_name": "accommodationNeeds", "field_label": "Accommodation Needs", "field_type": "textarea", "is_required": False, "order_index": 305, "section": "travel"},
    {"field_name": "dailyMeals", "field_label": "Daily Meals (if travelling daily)", "field_type": "select", "field_options": json.dumps(["Breakfast", "Lunch", "Dinner"]), "is_required": False, "order_index": 306, "section": "travel"},

    # Final Details Section (401-405)
    {"field_name": "certificateName", "field_label": "Name for Certificate", "field_type": "text", "is_required": False, "order_index": 401, "section": "final"},
    {"field_name": "badgeName", "field_label": "Name for Badge", "field_type": "text", "is_required": False, "order_index": 402, "section": "final"},
    {"field_name": "motivationLetter", "field_label": "Motivation Letter", "field_type": "textarea", "is_required": False, "order_index": 403, "section": "final"},
    {"field_name": "codeOfConductConfirm", "field_label": "Code of Conduct Confirmation", "field_type": "select", "field_options": json.dumps(["I agree"]), "is_required": True, "order_index": 404, "section": "final"},
    {"field_name": "travelRequirementsConfirm", "field_label": "Travel Requirements Confirmation", "field_type": "select", "field_options": json.dumps(["I confirm"]), "is_required": True, "order_index": 405, "section": "final"},
]

print(f"\nInitializing {len(default_fields)} default form fields for event {EVENT_ID}...")
print("="*60)

db = next(get_db())

try:
    # Check if fields already exist
    existing = db.query(FormField).filter(FormField.event_id == EVENT_ID).all()

    if existing:
        print(f"\n Found {len(existing)} existing fields for event {EVENT_ID}")
        response = input("Do you want to DELETE all existing fields and recreate them? (yes/no): ")

        if response.lower() == 'yes':
            for field in existing:
                db.delete(field)
            db.commit()
            print(f" Deleted {len(existing)} existing fields")
        else:
            print(" Skipping - keeping existing fields")
            sys.exit(0)

    # Create all default fields
    created_count = 0
    for field_data in default_fields:
        form_field = FormField(
            event_id=EVENT_ID,
            **field_data
        )
        db.add(form_field)
        created_count += 1

    db.commit()

    print(f"\n SUCCESS: Created {created_count} default form fields!")
    print("="*60)
    print("\n Now reload your portal page to see all the fields!")

except Exception as e:
    db.rollback()
    print(f"\n ERROR: {str(e)}")
    print("="*60)
finally:
    db.close()
