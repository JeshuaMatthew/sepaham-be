//! Read-only reference / content endpoints. These back the frontend's content
//! services (roles, onboarding questions, badges, roadmap catalog + trees,
//! internship contacts, AI feed, lofi tracks, community servers/channels).
//! All public — they return seeded/authored content, no per-user state.

use axum::extract::State;
use axum::routing::get;
use axum::{Json, Router};
use serde::{Deserialize, Serialize};
use serde_json::json;

use crate::auth::extractor::FacultyUser;
use crate::error::AppResult;
use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/roles", get(list_roles))
        .route("/onboarding/questions", get(list_questions).put(save_questions))
        .route("/badges", get(list_badges))
        .route("/internships/contacts", get(list_internship_contacts))
        .route("/music/lofi", get(list_lofi))
        .route("/community/servers", get(list_servers))
        .route("/community/channels", get(list_channels))
}

// ---------------------------------------------------------------------------
// Roles
// ---------------------------------------------------------------------------
#[derive(Serialize, sqlx::FromRow)]
#[serde(rename_all = "camelCase")]
struct RoleDto {
    id: String,
    title: String,
    emoji: String,
    tagline: String,
    description: String,
    accent: String,
    match_tags: Vec<String>,
    tech_stack: Vec<String>,
}

async fn list_roles(State(state): State<AppState>) -> AppResult<Json<serde_json::Value>> {
    let roles = sqlx::query_as::<_, RoleDto>(
        "SELECT id, title, emoji, tagline, description, accent, match_tags, tech_stack
         FROM roles ORDER BY sort_order",
    )
    .fetch_all(&state.pool)
    .await?;
    Ok(Json(json!({ "roles": roles })))
}

// ---------------------------------------------------------------------------
// Onboarding questions
// ---------------------------------------------------------------------------
#[derive(Serialize, sqlx::FromRow)]
#[serde(rename_all = "camelCase")]
struct QuestionDto {
    id: String,
    text: String,
    role_id: String,
}

async fn list_questions(State(state): State<AppState>) -> AppResult<Json<serde_json::Value>> {
    let questions = sqlx::query_as::<_, QuestionDto>(
        "SELECT id, text, role_id FROM onboarding_questions ORDER BY sort_order",
    )
    .fetch_all(&state.pool)
    .await?;
    Ok(Json(json!({ "questions": questions })))
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct QuestionInput {
    id: String,
    text: String,
    role_id: String,
}

#[derive(Deserialize)]
struct SaveQuestionsInput {
    questions: Vec<QuestionInput>,
}

/// PUT /api/onboarding/questions — faculty replaces the whole questionnaire.
async fn save_questions(
    State(state): State<AppState>,
    _faculty: FacultyUser,
    Json(input): Json<SaveQuestionsInput>,
) -> AppResult<Json<serde_json::Value>> {
    let mut tx = state.pool.begin().await?;
    sqlx::query("DELETE FROM onboarding_questions")
        .execute(&mut *tx)
        .await?;
    for (i, q) in input.questions.iter().enumerate() {
        sqlx::query(
            "INSERT INTO onboarding_questions (id, text, role_id, sort_order)
             VALUES ($1, $2, $3, $4)",
        )
        .bind(&q.id)
        .bind(&q.text)
        .bind(&q.role_id)
        .bind(i as i32)
        .execute(&mut *tx)
        .await?;
    }
    tx.commit().await?;
    Ok(Json(json!({ "ok": true, "count": input.questions.len() })))
}

// ---------------------------------------------------------------------------
// Badges (catalog; `earned` is false without a user context)
// ---------------------------------------------------------------------------
#[derive(Serialize, sqlx::FromRow)]
#[serde(rename_all = "camelCase")]
struct BadgeDto {
    id: String,
    name: String,
    description: String,
    icon: String,
    tier: String,
    earned: bool,
}

async fn list_badges(State(state): State<AppState>) -> AppResult<Json<serde_json::Value>> {
    let badges = sqlx::query_as::<_, BadgeDto>(
        "SELECT id, name, description, icon, tier::text AS tier, false AS earned
         FROM badges ORDER BY sort_order",
    )
    .fetch_all(&state.pool)
    .await?;
    Ok(Json(json!({ "badges": badges })))
}

// ---------------------------------------------------------------------------
// Internship contacts
// ---------------------------------------------------------------------------
#[derive(Serialize, sqlx::FromRow)]
#[serde(rename_all = "camelCase")]
struct InternshipContactDto {
    id: String,
    company: String,
    emoji: String,
    position: String,
    role_id: Option<String>,
    location: String,
    #[serde(rename = "type")]
    type_val: String,
    pic: String,
    contact: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    note: Option<String>,
}

async fn list_internship_contacts(
    State(state): State<AppState>,
) -> AppResult<Json<serde_json::Value>> {
    let contacts = sqlx::query_as::<_, InternshipContactDto>(
        "SELECT id, company, emoji, position, role_id, location, type AS type_val,
                pic, contact, note
         FROM internship_contacts ORDER BY id",
    )
    .fetch_all(&state.pool)
    .await?;
    Ok(Json(json!({ "contacts": contacts })))
}

// ---------------------------------------------------------------------------
// Lofi tracks
// ---------------------------------------------------------------------------
#[derive(Serialize, sqlx::FromRow)]
struct TrackDto {
    id: String,
    title: String,
    artist: String,
}

async fn list_lofi(State(state): State<AppState>) -> AppResult<Json<serde_json::Value>> {
    let tracks = sqlx::query_as::<_, TrackDto>("SELECT id, title, artist FROM lofi_tracks ORDER BY id")
        .fetch_all(&state.pool)
        .await?;
    Ok(Json(json!({ "tracks": tracks })))
}

// ---------------------------------------------------------------------------
// Community servers + channels
// ---------------------------------------------------------------------------
#[derive(Serialize, sqlx::FromRow)]
struct ServerDto {
    id: String,
    name: String,
    initial: String,
    color: String,
}

async fn list_servers(State(state): State<AppState>) -> AppResult<Json<serde_json::Value>> {
    let servers = sqlx::query_as::<_, ServerDto>(
        "SELECT id, name, initial, color FROM servers WHERE NOT banned ORDER BY created_at",
    )
    .fetch_all(&state.pool)
    .await?;
    Ok(Json(json!({ "servers": servers })))
}

#[derive(Serialize, sqlx::FromRow)]
#[serde(rename_all = "camelCase")]
struct ChannelDto {
    id: String,
    server_id: String,
    name: String,
    topic: String,
    kind: String,
}

async fn list_channels(State(state): State<AppState>) -> AppResult<Json<serde_json::Value>> {
    let channels = sqlx::query_as::<_, ChannelDto>(
        "SELECT id, server_id, name, topic, kind::text AS kind
         FROM channels ORDER BY server_id, sort_order",
    )
    .fetch_all(&state.pool)
    .await?;
    Ok(Json(json!({ "channels": channels })))
}
