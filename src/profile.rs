//! Per-user profile + onboarding preferences (auth required).

use axum::extract::State;
use axum::routing::get;
use axum::{Json, Router};
use serde::{Deserialize, Serialize};

use crate::auth::extractor::AuthUser;
use crate::error::AppResult;
use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/profile", get(get_profile).put(update_profile))
        .route("/preferences", get(get_preferences).put(update_preferences))
}

// ---------------------------------------------------------------------------
// Profile
// ---------------------------------------------------------------------------
#[derive(Serialize, sqlx::FromRow)]
#[serde(rename_all = "camelCase")]
struct ProfileDto {
    avatar_url: String,
    name: String,
    username: String,
    university: String,
    batch: i32,
    #[serde(rename = "role")]
    role_title: String,
    role_emoji: String,
    bio: String,
    location: String,
    github_connected: bool,
    github_username: Option<String>,
}

async fn fetch_profile(state: &AppState, user_id: uuid::Uuid) -> AppResult<ProfileDto> {
    let profile = sqlx::query_as::<_, ProfileDto>(
        "SELECT COALESCE(p.avatar_url, '') AS avatar_url,
                u.name,
                COALESCE(p.username, '') AS username,
                COALESCE(p.university, '') AS university,
                COALESCE(p.batch, 0) AS batch,
                COALESCE(p.role_title, '') AS role_title,
                COALESCE(p.role_emoji, '') AS role_emoji,
                COALESCE(p.bio, '') AS bio,
                COALESCE(p.location, '') AS location,
                COALESCE(p.github_connected, false) AS github_connected,
                p.github_username
         FROM users u
         LEFT JOIN profiles p ON p.user_id = u.id
         WHERE u.id = $1",
    )
    .bind(user_id)
    .fetch_one(&state.pool)
    .await?;
    Ok(profile)
}

async fn get_profile(
    State(state): State<AppState>,
    auth: AuthUser,
) -> AppResult<Json<ProfileDto>> {
    Ok(Json(fetch_profile(&state, auth.id).await?))
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct ProfileInput {
    avatar_url: Option<String>,
    name: Option<String>,
    username: Option<String>,
    university: Option<String>,
    batch: Option<i32>,
    #[serde(rename = "role")]
    role_title: Option<String>,
    role_emoji: Option<String>,
    bio: Option<String>,
    location: Option<String>,
}

/// Partial update: only fields present in the body are changed (COALESCE keeps
/// the existing value when a field is null/absent).
async fn update_profile(
    State(state): State<AppState>,
    auth: AuthUser,
    Json(input): Json<ProfileInput>,
) -> AppResult<Json<ProfileDto>> {
    let mut tx = state.pool.begin().await?;

    sqlx::query(
        "UPDATE profiles SET
            avatar_url = COALESCE($2, avatar_url),
            username   = COALESCE($3, username),
            university = COALESCE($4, university),
            batch      = COALESCE($5, batch),
            role_title = COALESCE($6, role_title),
            role_emoji = COALESCE($7, role_emoji),
            bio        = COALESCE($8, bio),
            location   = COALESCE($9, location),
            updated_at = now()
         WHERE user_id = $1",
    )
    .bind(auth.id)
    .bind(&input.avatar_url)
    .bind(&input.username)
    .bind(&input.university)
    .bind(input.batch)
    .bind(&input.role_title)
    .bind(&input.role_emoji)
    .bind(&input.bio)
    .bind(&input.location)
    .execute(&mut *tx)
    .await?;

    if let Some(name) = &input.name {
        sqlx::query("UPDATE users SET name = $2, updated_at = now() WHERE id = $1")
            .bind(auth.id)
            .bind(name)
            .execute(&mut *tx)
            .await?;
    }

    tx.commit().await?;

    Ok(Json(fetch_profile(&state, auth.id).await?))
}

// ---------------------------------------------------------------------------
// Preferences (onboarding questionnaire result)
// ---------------------------------------------------------------------------
#[derive(Serialize, sqlx::FromRow)]
#[serde(rename_all = "camelCase")]
struct PreferenceDto {
    role_id: Option<String>,
    role_title: String,
    role_emoji: String,
    role_scores: serde_json::Value,
}

/// Returns the user's saved preference, or `null` if they haven't onboarded.
async fn get_preferences(
    State(state): State<AppState>,
    auth: AuthUser,
) -> AppResult<Json<Option<PreferenceDto>>> {
    let pref = sqlx::query_as::<_, PreferenceDto>(
        "SELECT role_id, role_title, role_emoji, role_scores
         FROM user_preferences WHERE user_id = $1",
    )
    .bind(auth.id)
    .fetch_optional(&state.pool)
    .await?;
    Ok(Json(pref))
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct PreferenceInput {
    role_id: Option<String>,
    #[serde(default)]
    role_title: String,
    #[serde(default)]
    role_emoji: String,
    #[serde(default = "empty_object")]
    role_scores: serde_json::Value,
}

fn empty_object() -> serde_json::Value {
    serde_json::json!({})
}

async fn update_preferences(
    State(state): State<AppState>,
    auth: AuthUser,
    Json(input): Json<PreferenceInput>,
) -> AppResult<Json<PreferenceDto>> {
    let pref = sqlx::query_as::<_, PreferenceDto>(
        "INSERT INTO user_preferences (user_id, role_id, role_title, role_emoji, role_scores)
         VALUES ($1, $2, $3, $4, $5::jsonb)
         ON CONFLICT (user_id) DO UPDATE SET
            role_id     = EXCLUDED.role_id,
            role_title  = EXCLUDED.role_title,
            role_emoji  = EXCLUDED.role_emoji,
            role_scores = EXCLUDED.role_scores,
            updated_at  = now()
         RETURNING role_id, role_title, role_emoji, role_scores",
    )
    .bind(auth.id)
    .bind(&input.role_id)
    .bind(&input.role_title)
    .bind(&input.role_emoji)
    .bind(&input.role_scores)
    .fetch_one(&state.pool)
    .await?;
    Ok(Json(pref))
}
