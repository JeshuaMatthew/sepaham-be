-- Sepaham initial schema.
-- Covers every domain the frontend needs: auth/profiles, roles & onboarding,
-- roadmaps (+ student progress), community/chat, collab ("Cari Tim"), career
-- signals (github/cv), faculty moderation, and reference/AI content.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------
CREATE TYPE user_role         AS ENUM ('student', 'faculty');
CREATE TYPE badge_tier        AS ENUM ('common', 'rare', 'epic', 'legendary');
CREATE TYPE channel_kind      AS ENUM ('text', 'anon');
CREATE TYPE roadmap_difficulty AS ENUM ('Beginner', 'Intermediate', 'Advanced');
CREATE TYPE collab_status     AS ENUM ('open', 'full');
CREATE TYPE applicant_status  AS ENUM ('pending', 'accepted', 'rejected');

-- ===========================================================================
-- Auth & profiles
-- ===========================================================================
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          user_role NOT NULL DEFAULT 'student',
    name          TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE profiles (
    user_id          UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    avatar_url       TEXT NOT NULL DEFAULT '',
    username         TEXT UNIQUE,
    university       TEXT NOT NULL DEFAULT '',
    batch            INTEGER,
    role_title       TEXT NOT NULL DEFAULT '',
    role_emoji       TEXT NOT NULL DEFAULT '',
    bio              TEXT NOT NULL DEFAULT '',
    location         TEXT NOT NULL DEFAULT '',
    -- Career signals
    github_connected BOOLEAN NOT NULL DEFAULT false,
    github_username  TEXT,
    cv_file_name     TEXT,
    cv_uploaded_at   TIMESTAMPTZ,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Badge catalog + which users earned them.
CREATE TABLE badges (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    icon        TEXT NOT NULL DEFAULT '',
    tier        badge_tier NOT NULL DEFAULT 'common',
    sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE user_badges (
    user_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    badge_id  TEXT NOT NULL REFERENCES badges(id) ON DELETE CASCADE,
    earned    BOOLEAN NOT NULL DEFAULT true,
    earned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, badge_id)
);

-- GitHub dev-card stats (populated by the GitHub integration).
CREATE TABLE github_stats (
    user_id        UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    username       TEXT NOT NULL,
    total_commits  INTEGER NOT NULL DEFAULT 0,
    current_streak INTEGER NOT NULL DEFAULT 0,
    longest_streak INTEGER NOT NULL DEFAULT 0,
    public_repos   INTEGER NOT NULL DEFAULT 0,
    top_languages  JSONB NOT NULL DEFAULT '[]'::jsonb,  -- [{name,percentage,color}]
    weeks          JSONB NOT NULL DEFAULT '[]'::jsonb,  -- number[][]
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE github_repos (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name           TEXT NOT NULL,
    description    TEXT NOT NULL DEFAULT '',
    stars          INTEGER NOT NULL DEFAULT 0,
    forks          INTEGER NOT NULL DEFAULT 0,
    language       TEXT NOT NULL DEFAULT '',
    language_color TEXT NOT NULL DEFAULT '',
    url            TEXT NOT NULL DEFAULT ''
);
CREATE INDEX idx_github_repos_user ON github_repos(user_id);

-- ===========================================================================
-- Roles, hobbies & onboarding questionnaire
-- ===========================================================================
CREATE TABLE roles (
    id          TEXT PRIMARY KEY,               -- e.g. "frontend-engineer"
    title       TEXT NOT NULL,
    emoji       TEXT NOT NULL DEFAULT '',
    tagline     TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    accent      TEXT NOT NULL DEFAULT '',
    match_tags  TEXT[] NOT NULL DEFAULT '{}',
    tech_stack  TEXT[] NOT NULL DEFAULT '{}',
    sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE hobbies (
    id         TEXT PRIMARY KEY,
    label      TEXT NOT NULL,
    emoji      TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0
);

-- Likert questionnaire (faculty-editable). Agreeing strengthens `role_id`.
CREATE TABLE onboarding_questions (
    id         TEXT PRIMARY KEY,                -- e.g. "q1"
    text       TEXT NOT NULL,
    role_id    TEXT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    sort_order INTEGER NOT NULL DEFAULT 0
);

-- Result of a user's onboarding: chosen role + per-role scores.
CREATE TABLE user_preferences (
    user_id     UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    role_id     TEXT REFERENCES roles(id) ON DELETE SET NULL,
    role_title  TEXT NOT NULL DEFAULT '',
    role_emoji  TEXT NOT NULL DEFAULT '',
    role_scores JSONB NOT NULL DEFAULT '{}'::jsonb,  -- { roleId: score }
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ===========================================================================
-- Roadmaps (skill trees) + student progress
-- ===========================================================================
CREATE TABLE roadmaps (
    id          TEXT PRIMARY KEY,               -- e.g. "frontend"
    role_id     TEXT REFERENCES roles(id) ON DELETE SET NULL,
    title       TEXT NOT NULL,
    emoji       TEXT NOT NULL DEFAULT '',
    color       TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    difficulty  roadmap_difficulty NOT NULL DEFAULT 'Beginner',
    match_tags  TEXT[] NOT NULL DEFAULT '{}',
    author      TEXT NOT NULL DEFAULT '',        -- faculty/creator display name
    style       JSONB NOT NULL DEFAULT '{}'::jsonb,  -- RoadmapStyle
    created_by  UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE roadmap_nodes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id      TEXT NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
    node_key        TEXT NOT NULL,              -- string id unique within roadmap
    title           TEXT NOT NULL,
    emoji           TEXT NOT NULL DEFAULT '',
    x               DOUBLE PRECISION NOT NULL DEFAULT 0,
    y               DOUBLE PRECISION NOT NULL DEFAULT 0,
    group_name      TEXT,
    image           TEXT,                       -- data URL uploaded by admin
    title_inside    BOOLEAN NOT NULL DEFAULT false,
    always_unlocked BOOLEAN NOT NULL DEFAULT false,
    optional        BOOLEAN NOT NULL DEFAULT false,
    article         TEXT,                       -- Markdown content
    submission      JSONB,                      -- NodeSubmission {type,prompt,questions,passingScore}
    resources       JSONB,                      -- legacy [{label,url}]
    missions        JSONB,                      -- legacy [{id,text}]
    sort_order      INTEGER NOT NULL DEFAULT 0,
    UNIQUE (roadmap_id, node_key)
);
CREATE INDEX idx_roadmap_nodes_roadmap ON roadmap_nodes(roadmap_id);

CREATE TABLE roadmap_edges (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id TEXT NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
    edge_key   TEXT NOT NULL,
    source_key TEXT NOT NULL,                   -- references node_key within roadmap
    target_key TEXT NOT NULL,
    dashed     BOOLEAN NOT NULL DEFAULT false,
    optional   BOOLEAN NOT NULL DEFAULT false,
    animated   BOOLEAN NOT NULL DEFAULT false,
    UNIQUE (roadmap_id, edge_key)
);
CREATE INDEX idx_roadmap_edges_roadmap ON roadmap_edges(roadmap_id);

-- A student's submission/progress for a single node.
CREATE TABLE submissions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    roadmap_id   TEXT NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
    node_key     TEXT NOT NULL,
    done         BOOLEAN NOT NULL DEFAULT false,
    file_name    TEXT,
    text_answer  TEXT,
    score        INTEGER,                       -- quiz score 0-100
    quiz_answers JSONB,                         -- { questionId: optionIndex }
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, roadmap_id, node_key)
);
CREATE INDEX idx_submissions_user ON submissions(user_id);

-- When a user last opened/worked a roadmap (drives "recently active" in catalog).
CREATE TABLE roadmap_activity (
    user_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    roadmap_id     TEXT NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, roadmap_id)
);

-- ===========================================================================
-- Community / chat
-- ===========================================================================
CREATE TABLE servers (
    id                TEXT PRIMARY KEY,          -- e.g. "itb" or "tim-xxxxxxxx"
    name              TEXT NOT NULL,
    initial           TEXT NOT NULL DEFAULT '',
    color             TEXT NOT NULL DEFAULT '',
    owner_id          UUID REFERENCES users(id) ON DELETE SET NULL,
    is_team_community BOOLEAN NOT NULL DEFAULT false,
    banned            BOOLEAN NOT NULL DEFAULT false,   -- faculty moderation
    banned_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    banned_at         TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE channels (
    id         TEXT PRIMARY KEY,                 -- e.g. "general"
    server_id  TEXT NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    topic      TEXT NOT NULL DEFAULT '',
    kind       channel_kind NOT NULL DEFAULT 'text',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_channels_server ON channels(server_id);

CREATE TABLE server_members (
    server_id TEXT NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    user_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (server_id, user_id)
);

-- Shareable invite links for team communities.
CREATE TABLE community_invites (
    token      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    server_id  TEXT NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ
);
CREATE INDEX idx_community_invites_server ON community_invites(server_id);

-- 1-on-1 direct conversations. user_low < user_high keeps a pair unique.
CREATE TABLE direct_conversations (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_low   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_high  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT dm_user_order CHECK (user_low < user_high),
    UNIQUE (user_low, user_high)
);

-- Messages live in either a channel or a DM. Threaded replies point at parent_id.
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id      TEXT REFERENCES channels(id) ON DELETE CASCADE,
    dm_id           UUID REFERENCES direct_conversations(id) ON DELETE CASCADE,
    parent_id       UUID REFERENCES messages(id) ON DELETE CASCADE,
    author_id       UUID REFERENCES users(id) ON DELETE SET NULL,
    author_name     TEXT NOT NULL,
    author_avatar   TEXT NOT NULL DEFAULT '',
    body            TEXT,
    code_language   TEXT,
    code_content    TEXT,
    attachment_name TEXT,
    attachment_kind TEXT,                        -- 'image' | 'file'
    attachment_size TEXT,
    anonymous       BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT message_belongs_somewhere
        CHECK (channel_id IS NOT NULL OR dm_id IS NOT NULL)
);
CREATE INDEX idx_messages_channel ON messages(channel_id) WHERE channel_id IS NOT NULL;
CREATE INDEX idx_messages_dm      ON messages(dm_id) WHERE dm_id IS NOT NULL;
CREATE INDEX idx_messages_parent  ON messages(parent_id) WHERE parent_id IS NOT NULL;

-- ===========================================================================
-- Collab ("Cari Tim")
-- ===========================================================================
CREATE TABLE collab_requests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id       UUID REFERENCES users(id) ON DELETE SET NULL,
    author_name     TEXT NOT NULL,
    author_avatar   TEXT NOT NULL DEFAULT '',
    author_role     TEXT NOT NULL DEFAULT '',
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    needed_roles    TEXT[] NOT NULL DEFAULT '{}',
    tech_stack      TEXT[] NOT NULL DEFAULT '{}',
    tags            TEXT[] NOT NULL DEFAULT '{}',
    repo_url        TEXT,
    community_id    TEXT REFERENCES servers(id) ON DELETE SET NULL,
    members_current INTEGER NOT NULL DEFAULT 1,
    members_needed  INTEGER NOT NULL DEFAULT 2,
    status          collab_status NOT NULL DEFAULT 'open',
    closed          BOOLEAN NOT NULL DEFAULT false,   -- faculty closed the request
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_collab_requests_author ON collab_requests(author_id);

CREATE TABLE collab_request_images (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES collab_requests(id) ON DELETE CASCADE,
    url        TEXT NOT NULL,                    -- data URL or object-storage URL
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_collab_images_request ON collab_request_images(request_id);

CREATE TABLE collab_applicants (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES collab_requests(id) ON DELETE CASCADE,
    user_id    UUID REFERENCES users(id) ON DELETE SET NULL,
    name       TEXT NOT NULL,
    avatar     TEXT NOT NULL DEFAULT '',
    role       TEXT NOT NULL DEFAULT '',
    message    TEXT,
    status     applicant_status NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_collab_applicants_request ON collab_applicants(request_id);

-- ===========================================================================
-- Reference / AI content
-- ===========================================================================
CREATE TABLE internship_contacts (
    id       TEXT PRIMARY KEY,
    company  TEXT NOT NULL,
    emoji    TEXT NOT NULL DEFAULT '',
    position TEXT NOT NULL,
    role_id  TEXT REFERENCES roles(id) ON DELETE SET NULL,
    location TEXT NOT NULL DEFAULT '',
    type     TEXT NOT NULL DEFAULT '',
    pic      TEXT NOT NULL DEFAULT '',
    contact  TEXT NOT NULL DEFAULT '',
    note     TEXT
);

CREATE TABLE dev_quotes (
    id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text   TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT ''
);

-- AI-feed internship suggestions (distinct from internship_contacts).
CREATE TABLE ai_internships (
    id            TEXT PRIMARY KEY,
    company       TEXT NOT NULL,
    emoji         TEXT NOT NULL DEFAULT '',
    role          TEXT NOT NULL,
    location      TEXT NOT NULL DEFAULT '',
    type          TEXT NOT NULL DEFAULT '',
    match_percent INTEGER NOT NULL DEFAULT 0,
    tags          TEXT[] NOT NULL DEFAULT '{}'
);

CREATE TABLE lofi_tracks (
    id     TEXT PRIMARY KEY,
    title  TEXT NOT NULL,
    artist TEXT NOT NULL DEFAULT ''
);
