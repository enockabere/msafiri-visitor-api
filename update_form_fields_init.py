import sys
sys.stdout.reconfigure(encoding='utf-8')

file_path = 'D:/development/msafiri-visitor-api/app/api/v1/endpoints/form_fields.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the default_fields section
old_section = '''    # Create default protected fields
    default_fields = [
        # Personal Information Section
        {"field_name": "firstName", "field_label": "First Name", "field_type": "text", "is_required": True, "order_index": 101, "section": "personal", "is_protected": True},
        {"field_name": "lastName", "field_label": "Last Name", "field_type": "text", "is_required": True, "order_index": 102, "section": "personal", "is_protected": True},
        {"field_name": "oc", "field_label": "What is your OC?", "field_type": "select", "field_options": json.dumps(["OCA", "OCB", "OCBA", "OCG", "OCP", "WACA"]), "is_required": True, "order_index": 103, "section": "personal", "is_protected": True},
        {"field_name": "contractStatus", "field_label": "Contract Status", "field_type": "select", "field_options": json.dumps(["On contract", "Between contracts"]), "is_required": True, "order_index": 104, "section": "personal", "is_protected": True},
        {"field_name": "genderIdentity", "field_label": "Gender Identity", "field_type": "select", "field_options": json.dumps(["Man", "Woman", "Non-binary", "Prefer to self-describe", "Prefer not to disclose"]), "is_required": True, "order_index": 105, "section": "personal", "is_protected": True},

        # Contact Details Section
        {"field_name": "personalEmail", "field_label": "Personal/Tembo Email Address", "field_type": "email", "is_required": True, "order_index": 201, "section": "contact", "is_protected": True},
        {"field_name": "phoneNumber", "field_label": "Phone Number", "field_type": "text", "is_required": True, "order_index": 202, "section": "contact", "is_protected": True},

        # Travel & Accommodation Section
        {"field_name": "travellingInternationally", "field_label": "Will you be travelling internationally?", "field_type": "select", "field_options": json.dumps(["Yes", "No"]), "is_required": True, "order_index": 301, "section": "travel"},
        {"field_name": "accommodationType", "field_label": "Accommodation Type", "field_type": "select", "field_options": json.dumps(["Staying at accommodation", "Travelling daily"]), "is_required": True, "order_index": 302, "section": "travel"},

        # Final Details Section
        {"field_name": "codeOfConductConfirm", "field_label": "Code of Conduct Confirmation", "field_type": "select", "field_options": json.dumps(["I agree"]), "is_required": True, "order_index": 401, "section": "final"},
    ]'''

new_section = '''    # Create default protected fields - ALL FIELDS
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
        {"field_name": "countryOfWork", "field_label": "Country of Work", "field_type": "text", "is_required": False, "order_index": 110, "section": "personal"},
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
    ]'''

if old_section in content:
    content = content.replace(old_section, new_section)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Updated initialization endpoint with all 28 default fields!")
    print("\nNow restart your backend API server:")
    print("1. Stop the API (Ctrl+C)")
    print("2. Restart: uvicorn app.main:app --reload")
    print("3. Reload the portal page to initialize fields")
else:
    print("ERROR: Could not find the section to replace")
