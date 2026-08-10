//! Real-time: a WebSocket that streams chat events to connected clients, and a
//! LiveKit access-token endpoint so the frontend can join a room for mic/video
//! group calls. Media flows through the LiveKit server, not this backend.

use axum::extract::ws::{Message, WebSocket, WebSocketUpgrade};
use axum::extract::{Query, State};
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::routing::{get, post};
use axum::{Json, Router};
use chrono::{Duration, Utc};
use jsonwebtoken::{encode, Algorithm, EncodingKey, Header};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tokio::sync::broadcast::error::RecvError;

use crate::auth::extractor::AuthUser;
use crate::auth::jwt::verify_token;
use crate::error::{AppError, AppResult};
use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/ws", get(ws_handler))
        .route("/calls/token", post(call_token))
}

// ---------------------------------------------------------------------------
// WebSocket — pushes chat events (JSON) to clients. Auth via ?token= since
// browsers can't set headers on a WebSocket handshake.
// ---------------------------------------------------------------------------
#[derive(Deserialize)]
struct WsQuery {
    token: String,
}

async fn ws_handler(
    ws: WebSocketUpgrade,
    State(state): State<AppState>,
    Query(q): Query<WsQuery>,
) -> Response {
    if verify_token(&q.token, &state.config.jwt_secret).is_err() {
        return StatusCode::UNAUTHORIZED.into_response();
    }
    ws.on_upgrade(move |socket| ws_loop(socket, state))
}

async fn ws_loop(mut socket: WebSocket, state: AppState) {
    let mut rx = state.events.subscribe();
    loop {
        tokio::select! {
            event = rx.recv() => match event {
                Ok(msg) => {
                    if socket.send(Message::Text(msg.into())).await.is_err() {
                        break;
                    }
                }
                Err(RecvError::Lagged(_)) => continue,
                Err(RecvError::Closed) => break,
            },
            incoming = socket.recv() => match incoming {
                Some(Ok(Message::Close(_))) | None => break,
                Some(Err(_)) => break,
                _ => {} // ping/pong/text from client — ignored
            },
        }
    }
}

// ---------------------------------------------------------------------------
// LiveKit access token (HS256 JWT signed with the LiveKit API secret)
// ---------------------------------------------------------------------------
#[derive(Deserialize)]
struct TokenInput {
    room: String,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct VideoGrant {
    room: String,
    room_join: bool,
    can_publish: bool,
    can_subscribe: bool,
    can_publish_data: bool,
}

#[derive(Serialize)]
struct LkClaims {
    exp: i64,
    nbf: i64,
    iss: String,
    sub: String,
    name: String,
    video: VideoGrant,
}

async fn call_token(
    State(state): State<AppState>,
    auth: AuthUser,
    Json(input): Json<TokenInput>,
) -> AppResult<Json<Value>> {
    let room = input.room.trim();
    if room.is_empty() {
        return Err(AppError::BadRequest("room is required".into()));
    }

    let name: String = sqlx::query_scalar("SELECT name FROM users WHERE id = $1")
        .bind(auth.id)
        .fetch_optional(&state.pool)
        .await?
        .ok_or(AppError::Unauthorized)?;

    let now = Utc::now();
    let claims = LkClaims {
        exp: (now + Duration::hours(6)).timestamp(),
        nbf: now.timestamp(),
        iss: state.config.livekit_api_key.clone(),
        sub: auth.id.to_string(),
        name: name.clone(),
        video: VideoGrant {
            room: room.to_string(),
            room_join: true,
            can_publish: true,
            can_subscribe: true,
            can_publish_data: true,
        },
    };

    let token = encode(
        &Header::new(Algorithm::HS256),
        &claims,
        &EncodingKey::from_secret(state.config.livekit_api_secret.as_bytes()),
    )
    .map_err(|e| AppError::Internal(format!("livekit token: {e}")))?;

    Ok(Json(json!({
        "token": token,
        "url": state.config.livekit_url,
        "identity": auth.id,
        "name": name,
        "room": room,
    })))
}
