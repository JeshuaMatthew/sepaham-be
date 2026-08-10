-- Reverse of 0001_init.up.sql. Drop in reverse dependency order.

DROP TABLE IF EXISTS lofi_tracks;
DROP TABLE IF EXISTS ai_internships;
DROP TABLE IF EXISTS dev_quotes;
DROP TABLE IF EXISTS internship_contacts;

DROP TABLE IF EXISTS collab_applicants;
DROP TABLE IF EXISTS collab_request_images;
DROP TABLE IF EXISTS collab_requests;

DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS direct_conversations;
DROP TABLE IF EXISTS community_invites;
DROP TABLE IF EXISTS server_members;
DROP TABLE IF EXISTS channels;
DROP TABLE IF EXISTS servers;

DROP TABLE IF EXISTS roadmap_activity;
DROP TABLE IF EXISTS submissions;
DROP TABLE IF EXISTS roadmap_edges;
DROP TABLE IF EXISTS roadmap_nodes;
DROP TABLE IF EXISTS roadmaps;

DROP TABLE IF EXISTS user_preferences;
DROP TABLE IF EXISTS onboarding_questions;
DROP TABLE IF EXISTS hobbies;
DROP TABLE IF EXISTS roles;

DROP TABLE IF EXISTS github_repos;
DROP TABLE IF EXISTS github_stats;
DROP TABLE IF EXISTS user_badges;
DROP TABLE IF EXISTS badges;
DROP TABLE IF EXISTS profiles;
DROP TABLE IF EXISTS users;

DROP TYPE IF EXISTS applicant_status;
DROP TYPE IF EXISTS collab_status;
DROP TYPE IF EXISTS roadmap_difficulty;
DROP TYPE IF EXISTS channel_kind;
DROP TYPE IF EXISTS badge_tier;
DROP TYPE IF EXISTS user_role;
