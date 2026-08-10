//! Community chat: channel messages (with threaded replies) + direct messages.
//! Shapes match the frontend `ChatMessage` / `DirectConversation` types.

use std::collections::HashMap;

use axum::extract::{Path, State};
use axum::http::StatusCode;
use axum::routing::{get, post};
use axum::{Json, Router};
use serde::Deserialize;
use serde_json::{json, Map, Value};
use uuid::Uuid;

use crate::auth::extractor::AuthUser;
use crate::error::{AppError, AppResult};
use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route(
            "/channels/{channel_id}/messages",
            get(list_channel_messages).post(send_channel_message),
        )
        .route("/dms", get(list_dms).post(open_dm))
        .route("/dms/{dm_id}/messages", post(send_dm_message))
}

// ---------------------------------------------------------------------------
// Shared message row → JSON
// ---------------------------------------------------------------------------
#[derive(sqlx::FromRow)]
struct MessageRow {
    id: Uuid,
    parent_id: Option<Uuid>,
    author_id: Option<Uuid>,
    author_name: String,
    author_avatar: String,
    timestamp: String,
    body: Option<String>,
    code_language: Option<String>,
    code_content: Option<String>,
    attachment_name: Option<String>,
    attachment_kind: Option<String>,
    attachment_size: Option<String>,
    anonymous: bool,
}

const MESSAGE_COLS: &str = "id, parent_id, author_id, author_name, author_avatar,
    to_char(created_at, 'HH24:MI') AS timestamp, body, code_language, code_content,
    attachment_name, attachment_kind, attachment_size, anonymous";

fn message_json(row: &MessageRow, replies: Vec<Value>) -> Value {
    let mut o = Map::new();
    o.insert("id".into(), json!(row.id));
    o.insert(
        "authorId".into(),
        json!(row
            .author_id
            .map(|id| id.to_string())
            .unwrap_or_else(|| "anon".into())),
    );
    o.insert("authorName".into(), json!(row.author_name));
    o.insert("authorAvatar".into(), json!(row.author_avatar));
    o.insert("timestamp".into(), json!(row.timestamp));
    if let Some(text) = &row.body {
        o.insert("text".into(), json!(text));
    }
    if let (Some(language), Some(content)) = (&row.code_language, &row.code_content) {
        o.insert("code".into(), json!({ "language": language, "content": content }));
    }
    if let Some(name) = &row.attachment_name {
        o.insert(
            "attachment".into(),
            json!({
                "name": name,
                "kind": row.attachment_kind.clone().unwrap_or_default(),
                "size": row.attachment_size.clone().unwrap_or_default(),
            }),
        );
    }
    o.insert("anonymous".into(), json!(row.anonymous));
    o.insert("replies".into(), Value::Array(replies));
    Value::Object(o)
}

/// Group flat rows into top-level messages each with their thread replies.
fn nest_messages(rows: &[MessageRow]) -> Vec<Value> {
    let mut replies_by_parent: HashMap<Uuid, Vec<Value>> = HashMap::new();
    for row in rows {
        if let Some(parent) = row.parent_id {
            replies_by_parent
                .entry(parent)
                .or_default()
                .push(message_json(row, Vec::new()));
        }
    }
    rows.iter()
        .filter(|r| r.parent_id.is_none())
        .map(|r| message_json(r, replies_by_parent.remove(&r.id).unwrap_or_default()))
        .collect()
}

#[derive(sqlx::FromRow)]
struct AuthorInfo {
    name: String,
    avatar: String,
}

async fn author_info(state: &AppState, user_id: Uuid) -> AppResult<AuthorInfo> {
    Ok(sqlx::query_as::<_, AuthorInfo>(
        "SELECT u.name, COALESCE(p.avatar_url, '') AS avatar
         FROM users u LEFT JOIN profiles p ON p.user_id = u.id WHERE u.id = $1",
    )
    .bind(user_id)
    .fetch_one(&state.pool)
    .await?)
}

// ---------------------------------------------------------------------------
// Send payload (shared by channel + DM sends)
// ---------------------------------------------------------------------------
#[derive(Deserialize)]
struct CodeInput {
    language: String,
    content: String,
}

#[derive(Deserialize)]
struct AttachmentInput {
    name: String,
    kind: String,
    size: String,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct SendInput {
    #[serde(default)]
    text: Option<String>,
    code: Option<CodeInput>,
    attachment: Option<AttachmentInput>,
    #[serde(default)]
    anonymous: bool,
    /** untuk balasan thread di channel */
    parent_id: Option<Uuid>,
}

/// Insert a message into a channel or a DM and return it as JSON.
async fn insert_message(
    state: &AppState,
    author: AuthUser,
    channel_id: Option<&str>,
    dm_id: Option<Uuid>,
    input: &SendInput,
) -> AppResult<Value> {
    let (author_name, author_avatar, author_id) = if input.anonymous {
        ("Anonim".to_string(), String::new(), None)
    } else {
        let info = author_info(state, author.id).await?;
        (info.name, info.avatar, Some(author.id))
    };

    let row = sqlx::query_as::<_, MessageRow>(&format!(
        "INSERT INTO messages
            (channel_id, dm_id, parent_id, author_id, author_name, author_avatar,
             body, code_language, code_content, attachment_name, attachment_kind,
             attachment_size, anonymous)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
         RETURNING {MESSAGE_COLS}"
    ))
    .bind(channel_id)
    .bind(dm_id)
    .bind(input.parent_id)
    .bind(author_id)
    .bind(&author_name)
    .bind(&author_avatar)
    .bind(input.text.as_deref())
    .bind(input.code.as_ref().map(|c| c.language.as_str()))
    .bind(input.code.as_ref().map(|c| c.content.as_str()))
    .bind(input.attachment.as_ref().map(|a| a.name.as_str()))
    .bind(input.attachment.as_ref().map(|a| a.kind.as_str()))
    .bind(input.attachment.as_ref().map(|a| a.size.as_str()))
    .bind(input.anonymous)
    .fetch_one(&state.pool)
    .await?;

    Ok(message_json(&row, Vec::new()))
}

// ---------------------------------------------------------------------------
// Channel messages
// ---------------------------------------------------------------------------
async fn list_channel_messages(
    State(state): State<AppState>,
    Path(channel_id): Path<String>,
) -> AppResult<Json<Value>> {
    let rows = sqlx::query_as::<_, MessageRow>(&format!(
        "SELECT {MESSAGE_COLS} FROM messages WHERE channel_id = $1 ORDER BY created_at"
    ))
    .bind(&channel_id)
    .fetch_all(&state.pool)
    .await?;

    Ok(Json(Value::Array(nest_messages(&rows))))
}

async fn send_channel_message(
    State(state): State<AppState>,
    auth: AuthUser,
    Path(channel_id): Path<String>,
    Json(input): Json<SendInput>,
) -> AppResult<(StatusCode, Json<Value>)> {
    let exists: Option<String> = sqlx::query_scalar("SELECT id FROM channels WHERE id = $1")
        .bind(&channel_id)
        .fetch_optional(&state.pool)
        .await?;
    if exists.is_none() {
        return Err(AppError::NotFound("channel not found".into()));
    }

    let message = insert_message(&state, auth, Some(&channel_id), None, &input).await?;
    Ok((StatusCode::CREATED, Json(message)))
}

// ---------------------------------------------------------------------------
// Direct messages
// ---------------------------------------------------------------------------
#[derive(sqlx::FromRow)]
struct DmRow {
    id: Uuid,
    other_id: Uuid,
    user_name: String,
    avatar: String,
    role: String,
}

async fn list_dms(State(state): State<AppState>, auth: AuthUser) -> AppResult<Json<Value>> {
    let convos = sqlx::query_as::<_, DmRow>(
        "SELECT dc.id,
                CASE WHEN dc.user_low = $1 THEN dc.user_high ELSE dc.user_low END AS other_id,
                u.name AS user_name,
                COALESCE(p.avatar_url, '') AS avatar,
                COALESCE(p.role_title, '') AS role
         FROM direct_conversations dc
         JOIN users u ON u.id = (CASE WHEN dc.user_low = $1 THEN dc.user_high ELSE dc.user_low END)
         LEFT JOIN profiles p ON p.user_id = u.id
         WHERE dc.user_low = $1 OR dc.user_high = $1
         ORDER BY dc.created_at DESC",
    )
    .bind(auth.id)
    .fetch_all(&state.pool)
    .await?;

    let mut out = Vec::new();
    for convo in &convos {
        let rows = sqlx::query_as::<_, MessageRow>(&format!(
            "SELECT {MESSAGE_COLS} FROM messages WHERE dm_id = $1 ORDER BY created_at"
        ))
        .bind(convo.id)
        .fetch_all(&state.pool)
        .await?;
        let messages: Vec<Value> = rows.iter().map(|r| message_json(r, Vec::new())).collect();

        out.push(json!({
            "id": convo.id,
            "userId": convo.other_id,
            "userName": convo.user_name,
            "avatar": convo.avatar,
            "role": convo.role,
            "online": true,
            "messages": messages,
        }));
    }

    Ok(Json(json!({ "dms": out })))
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct OpenDmInput {
    user_id: Uuid,
}

async fn open_dm(
    State(state): State<AppState>,
    auth: AuthUser,
    Json(input): Json<OpenDmInput>,
) -> AppResult<Json<Value>> {
    if input.user_id == auth.id {
        return Err(AppError::BadRequest("cannot DM yourself".into()));
    }
    let (low, high) = if auth.id < input.user_id {
        (auth.id, input.user_id)
    } else {
        (input.user_id, auth.id)
    };

    let id: Uuid = sqlx::query_scalar(
        "INSERT INTO direct_conversations (user_low, user_high) VALUES ($1, $2)
         ON CONFLICT (user_low, user_high) DO UPDATE SET user_low = EXCLUDED.user_low
         RETURNING id",
    )
    .bind(low)
    .bind(high)
    .fetch_one(&state.pool)
    .await?;

    let other = author_info(&state, input.user_id).await?;
    Ok(Json(json!({
        "id": id,
        "userId": input.user_id,
        "userName": other.name,
        "avatar": other.avatar,
        "role": "",
        "online": true,
        "messages": [],
    })))
}

async fn send_dm_message(
    State(state): State<AppState>,
    auth: AuthUser,
    Path(dm_id): Path<Uuid>,
    Json(input): Json<SendInput>,
) -> AppResult<(StatusCode, Json<Value>)> {
    let is_participant: Option<Uuid> = sqlx::query_scalar(
        "SELECT id FROM direct_conversations
         WHERE id = $1 AND (user_low = $2 OR user_high = $2)",
    )
    .bind(dm_id)
    .bind(auth.id)
    .fetch_optional(&state.pool)
    .await?;
    if is_participant.is_none() {
        return Err(AppError::Forbidden);
    }

    // DMs never anonymous.
    let payload = SendInput {
        anonymous: false,
        ..input
    };
    let message = insert_message(&state, auth, None, Some(dm_id), &payload).await?;
    Ok((StatusCode::CREATED, Json(message)))
}