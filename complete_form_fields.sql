-- Complete form fields initialization for all events
-- This will add all the standard registration form fields

-- Personal Information Section (101-199)
INSERT INTO form_fields (event_id, field_name, field_label, field_type, is_required, order_index, is_protected, section)
SELECT e.id, 'oc', 'Operational Center (OC)', 'select', true, 103, true, 'personal'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'oc');

INSERT INTO form_fields (event_id, field_name, field_label, field_type, field_options, is_required, order_index, is_protected, section)
SELECT e.id, 'contractStatus', 'Contract Status', 'select', 
ARRAY['National Staff', 'International Staff', 'Consultant', 'Volunteer'], 
true, 104, true, 'personal'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'contractStatus');

INSERT INTO form_fields (event_id, field_name, field_label, field_type, field_options, is_required, order_index, is_protected, section)
SELECT e.id, 'contractType', 'Contract Type', 'select', 
ARRAY['Fixed Term', 'Permanent', 'Temporary', 'Project Based'], 
true, 105, true, 'personal'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'contractType');

INSERT INTO form_fields (event_id, field_name, field_label, field_type, field_options, is_required, order_index, is_protected, section)
SELECT e.id, 'genderIdentity', 'Gender Identity', 'select', 
ARRAY['Male', 'Female', 'Non-binary', 'Prefer not to say'], 
true, 106, true, 'personal'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'genderIdentity');

INSERT INTO form_fields (event_id, field_name, field_label, field_type, field_options, is_required, order_index, is_protected, section)
SELECT e.id, 'sex', 'Sex', 'select', 
ARRAY['Male', 'Female', 'Prefer not to say'], 
false, 107, false, 'personal'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'sex');

INSERT INTO form_fields (event_id, field_name, field_label, field_type, is_required, order_index, is_protected, section)
SELECT e.id, 'pronouns', 'Pronouns', 'text', false, 108, false, 'personal'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'pronouns');

INSERT INTO form_fields (event_id, field_name, field_label, field_type, is_required, order_index, is_protected, section)
SELECT e.id, 'currentPosition', 'Current Position', 'text', true, 109, true, 'personal'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'currentPosition');

INSERT INTO form_fields (event_id, field_name, field_label, field_type, field_options, is_required, order_index, is_protected, section)
SELECT e.id, 'countryOfWork', 'Country of Work', 'select', 
ARRAY['API_COUNTRIES'], 
false, 110, false, 'personal'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'countryOfWork');

INSERT INTO form_fields (event_id, field_name, field_label, field_type, is_required, order_index, is_protected, section)
SELECT e.id, 'projectOfWork', 'Project of Work', 'text', false, 111, false, 'personal'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'projectOfWork');

-- Contact Details Section (201-299)
INSERT INTO form_fields (event_id, field_name, field_label, field_type, is_required, order_index, is_protected, section)
SELECT e.id, 'msfEmail', 'MSF Email', 'email', false, 202, false, 'contact'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'msfEmail');

INSERT INTO form_fields (event_id, field_name, field_label, field_type, is_required, order_index, is_protected, section)
SELECT e.id, 'hrcoEmail', 'HRCO Email', 'email', false, 203, false, 'contact'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'hrcoEmail');

INSERT INTO form_fields (event_id, field_name, field_label, field_type, is_required, order_index, is_protected, section)
SELECT e.id, 'careerManagerEmail', 'Career Manager Email', 'email', false, 204, false, 'contact'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'careerManagerEmail');

INSERT INTO form_fields (event_id, field_name, field_label, field_type, is_required, order_index, is_protected, section)
SELECT e.id, 'lineManagerEmail', 'Line Manager Email', 'email', false, 205, false, 'contact'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'lineManagerEmail');

INSERT INTO form_fields (event_id, field_name, field_label, field_type, is_required, order_index, is_protected, section)
SELECT e.id, 'phoneNumber', 'Phone Number', 'text', true, 206, true, 'contact'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'phoneNumber');

-- Travel & Accommodation Section (301-399)
INSERT INTO form_fields (event_id, field_name, field_label, field_type, field_options, is_required, order_index, is_protected, section)
SELECT e.id, 'travellingInternationally', 'Are you travelling internationally?', 'select', 
ARRAY['Yes', 'No'], 
true, 301, true, 'travel'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'travellingInternationally');

INSERT INTO form_fields (event_id, field_name, field_label, field_type, field_options, is_required, order_index, is_protected, section)
SELECT e.id, 'travellingFromCountry', 'Which country are you travelling from?', 'select', 
ARRAY['API_COUNTRIES'], 
false, 302, true, 'travel'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'travellingFromCountry');

INSERT INTO form_fields (event_id, field_name, field_label, field_type, field_options, is_required, order_index, is_protected, section)
SELECT e.id, 'accommodationType', 'Accommodation Type', 'select', 
ARRAY['Staying at venue', 'Travelling daily'], 
true, 303, true, 'travel'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'accommodationType');

INSERT INTO form_fields (event_id, field_name, field_label, field_type, is_required, order_index, is_protected, section)
SELECT e.id, 'dietaryRequirements', 'Dietary Requirements', 'textarea', false, 304, true, 'travel'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'dietaryRequirements');

INSERT INTO form_fields (event_id, field_name, field_label, field_type, is_required, order_index, is_protected, section)
SELECT e.id, 'accommodationNeeds', 'Special Accommodation Needs', 'textarea', false, 305, false, 'travel'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'accommodationNeeds');

-- Final Details Section (401-499)
INSERT INTO form_fields (event_id, field_name, field_label, field_type, is_required, order_index, is_protected, section)
SELECT e.id, 'certificateName', 'Name for Certificate', 'text', false, 401, false, 'final'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'certificateName');

INSERT INTO form_fields (event_id, field_name, field_label, field_type, is_required, order_index, is_protected, section)
SELECT e.id, 'badgeName', 'Name for Badge', 'text', false, 402, false, 'final'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'badgeName');

INSERT INTO form_fields (event_id, field_name, field_label, field_type, is_required, order_index, is_protected, section)
SELECT e.id, 'motivationLetter', 'Motivation Letter', 'richtext', false, 403, false, 'final'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'motivationLetter');

INSERT INTO form_fields (event_id, field_name, field_label, field_type, field_options, is_required, order_index, is_protected, section)
SELECT e.id, 'codeOfConductConfirm', 'I confirm that I have read and agree to abide by the MSF Code of Conduct', 'checkbox', 
ARRAY['I agree'], 
true, 404, true, 'final'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'codeOfConductConfirm');

INSERT INTO form_fields (event_id, field_name, field_label, field_type, field_options, is_required, order_index, is_protected, section)
SELECT e.id, 'travelRequirementsConfirm', 'I understand and accept the travel requirements for this event', 'checkbox', 
ARRAY['I understand'], 
true, 405, true, 'final'
FROM events e
WHERE NOT EXISTS (SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'travelRequirementsConfirm');

COMMIT;