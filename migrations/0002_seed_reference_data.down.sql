-- Remove seeded reference data.
DELETE FROM lofi_tracks;
DELETE FROM ai_internships;
DELETE FROM dev_quotes;
DELETE FROM internship_contacts;
DELETE FROM roadmaps WHERE id IN ('frontend', 'backend', 'data', 'mobile');
DELETE FROM channels WHERE server_id IN ('itb', 'ui', 'ugm');
DELETE FROM servers WHERE id IN ('itb', 'ui', 'ugm');
DELETE FROM badges;
DELETE FROM onboarding_questions;
DELETE FROM hobbies;
DELETE FROM roles;
