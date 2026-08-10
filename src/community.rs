//! Community membership + invite links. Campus servers & channels are listed by
//! `catalog.rs`; this module handles joining, the user's own communities, and
//! shareable invite tokens.

use axum::extract::{Path, State};
use axum::http::StatusCode;
use axum::routing::{get, post};
use axum::{Json, Router};
use serde::Serialize;
use serde_json::{json, Value};
use uuid::Uuid;

use crate::auth::extractor::AuthUser;
use crate::error::{AppError, AppResult};
use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/community/mine", get(my_communities))
        .route("/community/servers/{id}/join", post(join_server))
        .route("/community/servers/{id}/invites", post(create_invite))
        .route("/community/invites/{token}/accept", post(accept_invite))
}

#[derive(Serialize, sqlx::FromRow)]
struct ServerDto {
    id: String,
    name: String,
    initial: String,
    color: String,
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

/// Build `{ server, channels }` for one server (the StoredCommunity shape).
async fn community_json(state: &AppState, server_id: &str) -> AppResult<Value> {
    let server = sqlx::query_as::<_, ServerDto>(
        "SELECT id, name, initial, color FROM servers WHERE id = $1",
    )
    .bind(server_id)
    .fetch_optional(&state.pool)
    .await?
    .ok_or_else(|| AppError::NotFound("community not found".into()))?;

    let channels = sqlx::query_as::<_, ChannelDto>(
        "SELECT id, server_id, name, topic, kind::text AS kind
         FROM channels WHERE server_id = $1 ORDER BY sort_order",
    )
    .bind(server_id)
    .fetch_all(&state.pool)
    .await?;

    Ok(json!({ "server": server, "channels": channels }))
}

async fn is_member(state: &AppState, server_id: &str, user_id: Uuid) -> AppResult<bool> {
    let found: Option<i32> = sqlx::query_scalar(
        "SELECT 1 FROM server_members WHERE server_id = $1 AND user_id = $2",
    )
    .bind(server_id)
    .bind(user_id)
    .fetch_optional(&state.pool)
    .await?;
    Ok(found.is_some())
}

/// Add a member (idempotent) and return the community. Errors if banned/missing.
async fn join(state: &AppState, server_id: &str, user_id: Uuid) -> AppResult<Value> {
    let banned: Option<bool> = sqlx::query_scalar("SELECT banned FROM servers WHERE id = $1")
        .bind(server_id)
        .fetch_optional(&state.pool)
        .await?;
    match banned {
        None => return Err(AppError::NotFound("community not found".into())),
        Some(true) => return Err(AppError::Forbidden),
        Some(false) => {}
    }

    sqlx::query(
        "INSERT INTO server_members (server_id, user_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
    )
    .bind(server_id)
    .bind(user_id)
    .execute(&state.pool)
    .await?;

    community_json(state, server_id).await
}

// ---------------------------------------------------------------------------
// GET /api/community/mine — communities the user belongs to (+ channels)
// ---------------------------------------------------------------------------
async fn my_communities(State(state): State<AppState>, auth: AuthUser) -> AppResult<Json<Value>> {
    let servers = sqlx::query_as::<_, ServerDto>(
        "SELECT s.id, s.name, s.initial, s.color
         FROM servers s
         JOIN server_members m ON m.server_id = s.id
         WHERE m.user_id = $1 AND NOT s.banned
         ORDER BY m.joined_at DESC",
    )
    .bind(auth.id)
    .fetch_all(&state.pool)
    .await?;

    let ids: Vec<String> = servers.iter().map(|s| s.id.clone()).collect();

    let channels = sqlx::query_as::<_, ChannelDto>(
        "SELECT id, server_id, name, topic, kind::text AS kind
         FROM channels WHERE server_id = ANY($1) ORDER BY server_id, sort_order",
    )
    .bind(&ids)
    .fetch_all(&state.pool)
    .await?;

    let communities: Vec<Value> = servers
        .iter()
        .map(|s| {
            let server_channels: Vec<&ChannelDto> =
                channels.iter().filter(|c| c.server_id == s.id).collect();
            json!({ "server": s, "channels": server_channels })
        })
        .collect();

    Ok(Json(json!({ "communities": communities })))
}

// ---------------------------------------------------------------------------
// POST /api/community/servers/{id}/join — join by server id (invite link)
// ---------------------------------------------------------------------------
async fn join_server(
    State(state): State<AppState>,
    auth: AuthUser,
    Path(id): Path<String>,
) -> AppResult<Json<Value>> {
    Ok(Json(join(&state, &id, auth.id).await?))
}

// ---------------------------------------------------------------------------
// POST /api/community/servers/{id}/invites — mint an invite token (members only)
// ---------------------------------------------------------------------------
async fn create_invite(
    State(state): State<AppState>,
    auth: AuthUser,
    Path(id): Path<String>,
) -> AppResult<(StatusCode, Json<Value>)> {
    if !is_member(&state, &id, auth.id).await? {
        return Err(AppError::Forbidden);
    }

    let token: Uuid = sqlx::query_scalar(
        "INSERT INTO community_invites (server_id, created_by) VALUES ($1, $2) RETURNING token",
    )
    .bind(&id)
    .bind(auth.id)
    .fetch_one(&state.pool)
    .await?;

    Ok((StatusCode::CREATED, Json(json!({ "token": token, "serverId": id }))))
}

// ---------------------------------------------------------------------------
// POST /api/community/invites/{token}/accept — join via an invite token
// ---------------------------------------------------------------------------
async fn accept_invite(
    State(state): State<AppState>,
    auth: AuthUser,
    Path(token): Path<Uuid>,
) -> AppResult<Json<Value>> {
    let server_id: Option<String> = sqlx::query_scalar(
        "SELECT server_id FROM community_invites
         WHERE token = $1 AND (expires_at IS NULL OR expires_at > now())",
    )
    .bind(token)
    .fetch_optional(&state.pool)
    .await?;

    let server_id = server_id.ok_or_else(|| AppError::NotFound("invite not found or expired".into()))?;

    Ok(Json(join(&state, &server_id, auth.id).await?))
}
