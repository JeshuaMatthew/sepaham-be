//! Context builder for AI requests.
//!
//! Pulls relevant data from PostgreSQL and formats it into a plain-text block
//! that gets injected into the Gemini prompt alongside the user's message.
//!
//! Two public entry points:
//! - `build`          — full context (Phase 2 general endpoint)
//! - `build_for`      — intent-targeted context (Phase 3 /assist endpoint)
//!
//! Gemini = reasoning layer. PostgreSQL = source of truth.

use sqlx::PgPool;
use uuid::Uuid;

use crate::ai::models::AiIntent;

// ---------------------------------------------------------------------------
// Internal DB row types
// ---------------------------------------------------------------------------

#[derive(sqlx::FromRow)]
struct RoleRow {
    id: String,
    title: String,
    emoji: String,
    tagline: String,
    description: String,
    tech_stack: Vec<String>,
    match_tags: Vec<String>,
}

#[derive(sqlx::FromRow)]
struct RoadmapRow {
    id: String,
    title: String,
    difficulty: String,
    description: String,
    role_id: Option<String>,
}

#[derive(sqlx::FromRow)]
struct RoadmapNodeRow {
    title: String,
    group_name: Option<String>,
}

#[derive(sqlx::FromRow)]
struct UserPreferenceRow {
    role_id: Option<String>,
    role_title: String,
    role_emoji: String,
}

#[derive(sqlx::FromRow)]
struct ProgressRow {
    roadmap_title: String,
    total: i64,
    completed: i64,
}

#[derive(sqlx::FromRow)]
struct InternshipRow {
    company: String,
    role: String,
    location: String,
    #[sqlx(rename = "type_val")]
    type_val: String,
    match_percent: i32,
    tags: Vec<String>,
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/// Full context — used by `POST /api/ai/generate` (Phase 2).
/// Includes all sections regardless of intent.
pub async fn build(pool: &PgPool, user_id: Uuid) -> String {
    build_sections(pool, user_id, &AiIntent::General).await
}

/// Intent-targeted context — used by `POST /api/ai/assist` (Phase 3).
/// Selects only the sections relevant to the given intent to keep prompt tight.
pub async fn build_for(pool: &PgPool, user_id: Uuid, intent: &AiIntent) -> String {
    build_sections(pool, user_id, intent).await
}

// ---------------------------------------------------------------------------
// Core builder
// ---------------------------------------------------------------------------

async fn build_sections(pool: &PgPool, user_id: Uuid, intent: &AiIntent) -> String {
    let mut parts: Vec<String> = Vec::new();

    let include_roles = matches!(
        intent,
        AiIntent::RecommendRole | AiIntent::CareerPath | AiIntent::General
    );
    let include_roadmaps = matches!(
        intent,
        AiIntent::ExplainRoadmap | AiIntent::CareerPath | AiIntent::General
    );
    let include_internships = matches!(
        intent,
        AiIntent::FindInternship | AiIntent::CareerPath | AiIntent::General
    );

    // --- Roles (with full description for targeted intents) ---
    if include_roles {
        if let Ok(roles) = fetch_roles(pool).await {
            if !roles.is_empty() {
                let mut section = String::from("## Available Roles in Sepaham\n");
                for r in &roles {
                    section.push_str(&format!(
                        "### {} {} (id: {})\n- Tagline: {}\n- Description: {}\n- Tech Stack: {}\n- Related interests: {}\n\n",
                        r.emoji, r.title, r.id,
                        r.tagline,
                        r.description,
                        r.tech_stack.join(", "),
                        r.match_tags.join(", ")
                    ));
                }
                parts.push(section);
            }
        }
    }

    // --- Roadmaps ---
    if include_roadmaps {
        if let Ok(roadmaps) = fetch_roadmaps(pool).await {
            if !roadmaps.is_empty() {
                let mut section = String::from("## Learning Roadmaps Available\n");
                for rm in &roadmaps {
                    section.push_str(&format!(
                        "### {} [{}] → role: {}\n{}\n\n",
                        rm.title,
                        rm.difficulty,
                        rm.role_id.as_deref().unwrap_or("general"),
                        rm.description
                    ));

                    // For ExplainRoadmap, also include top-level node groups
                    if matches!(intent, AiIntent::ExplainRoadmap) {
                        if let Ok(nodes) = fetch_roadmap_groups(pool, &rm.id).await {
                            if !nodes.is_empty() {
                                let groups: Vec<String> = nodes
                                    .iter()
                                    .filter_map(|n| n.group_name.as_deref())
                                    .collect::<std::collections::HashSet<_>>()
                                    .into_iter()
                                    .map(String::from)
                                    .collect();
                                if !groups.is_empty() {
                                    section.push_str(&format!(
                                        "Topics covered: {}\n\n",
                                        groups.join(", ")
                                    ));
                                }
                                // List first 10 node titles as a sample
                                let sample: Vec<&str> =
                                    nodes.iter().take(10).map(|n| n.title.as_str()).collect();
                                section.push_str(&format!(
                                    "Sample nodes: {}\n\n",
                                    sample.join(", ")
                                ));
                            }
                        }
                    }
                }
                parts.push(section);
            }
        }
    }

    // --- User preference ---
    if let Ok(Some(pref)) = fetch_user_preference(pool, user_id).await {
        let mut section = format!(
            "## Current User's Chosen Role\n{} {} (id: {})\n",
            pref.role_emoji,
            pref.role_title,
            pref.role_id.as_deref().unwrap_or("unknown")
        );

        // For career & roadmap intents, include internship contacts filtered by role
        if matches!(intent, AiIntent::CareerPath | AiIntent::FindInternship) {
            if let Some(role_id) = &pref.role_id {
                if let Ok(contacts) = fetch_internship_contacts(pool, role_id).await {
                    if !contacts.is_empty() {
                        section.push_str("\n### Internship Contacts for This Role\n");
                        for c in &contacts {
                            section.push_str(&format!(
                                "- {} at {} ({}, {}) — Contact: {}\n",
                                c.position, c.company, c.location, c.type_val, c.pic
                            ));
                        }
                    }
                }
            }
        }
        parts.push(section);
    }

    // --- User roadmap progress ---
    if let Ok(progress) = fetch_user_progress(pool, user_id).await {
        if !progress.is_empty() {
            let mut section = String::from("## Current User's Roadmap Progress\n");
            for p in &progress {
                let pct = if p.total > 0 {
                    (p.completed * 100) / p.total
                } else {
                    0
                };
                section.push_str(&format!(
                    "- **{}**: {}/{} nodes completed ({}%)\n",
                    p.roadmap_title, p.completed, p.total, pct
                ));
            }
            parts.push(section);
        }
    }

    // --- Internship suggestions from ai_internships ---
    if include_internships {
        if let Ok(internships) = fetch_internships(pool).await {
            if !internships.is_empty() {
                let mut section = String::from("## Internship Opportunities Available\n");
                for i in &internships {
                    section.push_str(&format!(
                        "- **{}** at {} ({}, {}) — {}% match | Skills: {}\n",
                        i.role,
                        i.company,
                        i.location,
                        i.type_val,
                        i.match_percent,
                        i.tags.join(", ")
                    ));
                }
                parts.push(section);
            }
        }
    }

    if parts.is_empty() {
        return String::new();
    }

    format!(
        "---\n# Sepaham Platform Data (Source of Truth)\n\
         Use this data to answer accurately. Do not fabricate data beyond what is listed here.\n\n\
         {}\n---\n",
        parts.join("\n")
    )
}

// ---------------------------------------------------------------------------
// Private query helpers
// ---------------------------------------------------------------------------

async fn fetch_roles(pool: &PgPool) -> Result<Vec<RoleRow>, sqlx::Error> {
    sqlx::query_as::<_, RoleRow>(
        "SELECT id, title, COALESCE(emoji, '') AS emoji, tagline, description,
                tech_stack, match_tags
         FROM roles ORDER BY sort_order",
    )
    .fetch_all(pool)
    .await
}

async fn fetch_roadmaps(pool: &PgPool) -> Result<Vec<RoadmapRow>, sqlx::Error> {
    sqlx::query_as::<_, RoadmapRow>(
        "SELECT id, title, difficulty::text AS difficulty, description, role_id
         FROM roadmaps ORDER BY created_at",
    )
    .fetch_all(pool)
    .await
}

/// Fetch node groups (and a sample of node titles) for a specific roadmap.
async fn fetch_roadmap_groups(
    pool: &PgPool,
    roadmap_id: &str,
) -> Result<Vec<RoadmapNodeRow>, sqlx::Error> {
    sqlx::query_as::<_, RoadmapNodeRow>(
        "SELECT title, group_name FROM roadmap_nodes
         WHERE roadmap_id = $1 ORDER BY sort_order LIMIT 30",
    )
    .bind(roadmap_id)
    .fetch_all(pool)
    .await
}

async fn fetch_user_preference(
    pool: &PgPool,
    user_id: Uuid,
) -> Result<Option<UserPreferenceRow>, sqlx::Error> {
    sqlx::query_as::<_, UserPreferenceRow>(
        "SELECT role_id, role_title, role_emoji
         FROM user_preferences WHERE user_id = $1",
    )
    .bind(user_id)
    .fetch_optional(pool)
    .await
}

async fn fetch_user_progress(
    pool: &PgPool,
    user_id: Uuid,
) -> Result<Vec<ProgressRow>, sqlx::Error> {
    sqlx::query_as::<_, ProgressRow>(
        "SELECT
            rm.title AS roadmap_title,
            (SELECT count(*) FROM roadmap_nodes n WHERE n.roadmap_id = rm.id) AS total,
            (SELECT count(*) FROM submissions s
             WHERE s.user_id = $1 AND s.roadmap_id = rm.id AND s.done) AS completed
         FROM roadmap_activity ra
         JOIN roadmaps rm ON rm.id = ra.roadmap_id
         WHERE ra.user_id = $1
         ORDER BY ra.last_active_at DESC
         LIMIT 5",
    )
    .bind(user_id)
    .fetch_all(pool)
    .await
}

async fn fetch_internships(pool: &PgPool) -> Result<Vec<InternshipRow>, sqlx::Error> {
    sqlx::query_as::<_, InternshipRow>(
        "SELECT company, role, location, type AS type_val, match_percent, tags
         FROM ai_internships ORDER BY match_percent DESC",
    )
    .fetch_all(pool)
    .await
}

// ---------------------------------------------------------------------------
// Internship contacts (from internship_contacts table, filtered by role)
// ---------------------------------------------------------------------------

#[derive(sqlx::FromRow)]
struct ContactRow {
    company: String,
    position: String,
    location: String,
    #[sqlx(rename = "type_val")]
    type_val: String,
    pic: String,
}

async fn fetch_internship_contacts(
    pool: &PgPool,
    role_id: &str,
) -> Result<Vec<ContactRow>, sqlx::Error> {
    sqlx::query_as::<_, ContactRow>(
        "SELECT company, position, location, type AS type_val, pic
         FROM internship_contacts WHERE role_id = $1 ORDER BY id",
    )
    .bind(role_id)
    .fetch_all(pool)
    .await
}
