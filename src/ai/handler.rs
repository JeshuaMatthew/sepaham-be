//! Axum route handlers for the AI module.
//!
//! # Endpoints
//!
//! | Method | Path              | Description                            |
//! |--------|-------------------|----------------------------------------|
//! | POST   | /api/ai/generate  | Phase 2 — general question with DB ctx |
//! | POST   | /api/ai/assist    | Phase 3 — intent-aware Sepaham AI      |
//!
//! Both require a valid JWT (`Authorization: Bearer <token>`).

use axum::extract::State;
use axum::http::StatusCode;
use axum::Json;

use crate::ai::context;
use crate::ai::models::{
    AiAssistRequest, AiErrorResponse, AiFeedInternship, AiFeedResponse, AiIntent, AiRequest,
    AiResponse, DevQuote, GithubNudge, MAX_MESSAGE_LEN,
};
use crate::ai::prompt::{
    build_system_prompt, INTENT_CAREER_PATH, INTENT_EXPLAIN_ROADMAP, INTENT_FIND_INTERNSHIP,
    INTENT_GENERAL, INTENT_RECOMMEND_ROLE,
};
use crate::ai::service::GeminiError;
use crate::auth::extractor::AuthUser;
use crate::state::AppState;

// ---------------------------------------------------------------------------
// Phase 1 — GET /api/ai/feed
// ---------------------------------------------------------------------------

// Internal DB row types used only in this handler.
#[derive(sqlx::FromRow)]
struct QuoteRow {
    text: String,
    author: String,
}

#[derive(sqlx::FromRow)]
struct GithubStatsRow {
    current_streak: i32,
}

#[derive(sqlx::FromRow)]
struct InternshipFeedRow {
    id: String,
    company: String,
    emoji: String,
    role: String,
    location: String,
    #[sqlx(rename = "type")]
    kind: String,
    match_percent: i32,
    tags: Vec<String>,
}

/// Home feed — returns a random dev quote, a GitHub activity nudge, and
/// internship suggestions from `ai_internships`.
///
/// Requires a valid JWT so the nudge can be personalised with the user's
/// current GitHub commit streak (falls back to zero if not connected).
///
/// # Response (200)
/// ```json
/// {
///   "quotes": [{ "text": "...", "author": "..." }],
///   "nudge":  { "title": "...", "message": "...", "streak": 5, "cta": "..." },
///   "internships": [{ "id": "i1", "company": "...", ... }]
/// }
/// ```
pub async fn feed(
    State(state): State<AppState>,
    auth: AuthUser,
) -> Result<Json<AiFeedResponse>, (StatusCode, Json<AiErrorResponse>)> {
    let pool = &state.pool;

    // --- 1. Random dev quote ---
    let quotes: Vec<DevQuote> = sqlx::query_as::<_, QuoteRow>(
        "SELECT text, author FROM dev_quotes ORDER BY random() LIMIT 1",
    )
    .fetch_all(pool)
    .await
    .unwrap_or_default()
    .into_iter()
    .map(|r| DevQuote { text: r.text, author: r.author })
    .collect();

    // --- 2. GitHub nudge (personalised with streak if connected) ---
    let streak: i32 = sqlx::query_as::<_, GithubStatsRow>(
        "SELECT current_streak FROM github_stats WHERE user_id = $1",
    )
    .bind(auth.id)
    .fetch_optional(pool)
    .await
    .unwrap_or(None)
    .map(|r| r.current_streak)
    .unwrap_or(0);

    let nudge = build_nudge(streak);

    // --- 3. Internship suggestions ---
    let internships: Vec<AiFeedInternship> = sqlx::query_as::<_, InternshipFeedRow>(
        "SELECT id, company, COALESCE(emoji, '') AS emoji, role,
                location, type, match_percent, tags
         FROM ai_internships ORDER BY match_percent DESC",
    )
    .fetch_all(pool)
    .await
    .unwrap_or_default()
    .into_iter()
    .map(|r| AiFeedInternship {
        id: r.id,
        company: r.company,
        emoji: r.emoji,
        role: r.role,
        location: r.location,
        kind: r.kind,
        match_percent: r.match_percent,
        tags: r.tags,
    })
    .collect();

    tracing::debug!(user_id = %auth.id, streak, "AI feed served");

    Ok(Json(AiFeedResponse { quotes, nudge, internships }))
}

/// Build a motivational GitHub nudge based on the user's current streak.
fn build_nudge(streak: i32) -> GithubNudge {
    if streak == 0 {
        GithubNudge {
            title: "Start your streak today".to_string(),
            message: "Push a commit to kick off your coding streak. Even a small one counts.".to_string(),
            streak: 0,
            cta: "Open GitHub".to_string(),
        }
    } else if streak < 3 {
        GithubNudge {
            title: format!("{streak}-day streak — keep going!"),
            message: "You're just getting started. Commit again today to build the habit.".to_string(),
            streak,
            cta: "Keep the streak".to_string(),
        }
    } else if streak < 7 {
        GithubNudge {
            title: format!("{streak}-day streak 🔥"),
            message: "Nice consistency! A few more days and you'll hit your first weekly streak.".to_string(),
            streak,
            cta: "Keep it up".to_string(),
        }
    } else if streak < 30 {
        GithubNudge {
            title: format!("{streak}-day streak — on fire!"),
            message: "You're in the zone. Recruiters love consistent GitHub activity.".to_string(),
            streak,
            cta: "Don't break it".to_string(),
        }
    } else {
        GithubNudge {
            title: format!("{streak}-day streak — legendary!"),
            message: "A month of daily commits. That's the kind of discipline that sets you apart.".to_string(),
            streak,
            cta: "Keep the legend alive".to_string(),
        }
    }
}

// ---------------------------------------------------------------------------
// Phase 2 — POST /api/ai/generate
// ---------------------------------------------------------------------------

/// General-purpose AI endpoint. Injects full DB context (roles, roadmaps,
/// user preference, progress, internships) and forwards the message to Gemini.
///
/// # Request
/// ```json
/// { "message": "Apa itu machine learning?" }
/// ```
///
/// # Response (200)
/// ```json
/// { "response": "Machine learning adalah..." }
/// ```
pub async fn generate(
    State(state): State<AppState>,
    auth: AuthUser,
    Json(payload): Json<AiRequest>,
) -> Result<Json<AiResponse>, (StatusCode, Json<AiErrorResponse>)> {
    let message = validate_message(payload.message)?;

    let ctx = context::build(&state.pool, auth.id).await;

    tracing::debug!(user_id = %auth.id, context_len = ctx.len(), "AI generate request");

    call_gemini(&state, &message, &ctx, INTENT_GENERAL, auth.id).await
}

// ---------------------------------------------------------------------------
// Phase 3 — POST /api/ai/assist
// ---------------------------------------------------------------------------

/// Intent-aware AI assistant. Selects the right prompt template and DB context
/// sections based on the declared `intent`.
///
/// # Request
/// ```json
/// {
///   "intent": "recommend_role",
///   "message": "Saya suka matematika dan programming, cocoknya jadi apa?"
/// }
/// ```
///
/// # Supported intents
/// - `recommend_role`   — rekomendasi role/jurusan berdasarkan minat
/// - `explain_roadmap`  — penjelasan roadmap + progres user
/// - `career_path`      — panduan karir step-by-step
/// - `find_internship`  — rekomendasi magang yang cocok
/// - `general`          — pertanyaan umum (default)
///
/// # Response (200)
/// ```json
/// { "response": "Berdasarkan minat kamu di matematika dan programming..." }
/// ```
pub async fn assist(
    State(state): State<AppState>,
    auth: AuthUser,
    Json(payload): Json<AiAssistRequest>,
) -> Result<Json<AiResponse>, (StatusCode, Json<AiErrorResponse>)> {
    let message = validate_message(payload.message)?;
    let intent = payload.intent;

    // Pick the intent-specific prompt addon
    let intent_prompt = match &intent {
        AiIntent::RecommendRole   => INTENT_RECOMMEND_ROLE,
        AiIntent::ExplainRoadmap  => INTENT_EXPLAIN_ROADMAP,
        AiIntent::CareerPath      => INTENT_CAREER_PATH,
        AiIntent::FindInternship  => INTENT_FIND_INTERNSHIP,
        AiIntent::General         => INTENT_GENERAL,
    };

    // Build intent-targeted DB context (only relevant sections)
    let ctx = context::build_for(&state.pool, auth.id, &intent).await;

    tracing::debug!(
        user_id  = %auth.id,
        intent   = ?intent,
        context_len = ctx.len(),
        "AI assist request"
    );

    call_gemini(&state, &message, &ctx, intent_prompt, auth.id).await
}

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

/// Trim and validate a message string. Returns `400` if empty or too long.
fn validate_message(
    raw: String,
) -> Result<String, (StatusCode, Json<AiErrorResponse>)> {
    let msg = raw.trim().to_string();

    if msg.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(AiErrorResponse {
                error: "Message cannot be empty.".to_string(),
            }),
        ));
    }

    if msg.len() > MAX_MESSAGE_LEN {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(AiErrorResponse {
                error: format!(
                    "Message exceeds maximum length of {MAX_MESSAGE_LEN} characters."
                ),
            }),
        ));
    }

    Ok(msg)
}

/// Build the system prompt, call Gemini, and map errors to HTTP responses.
async fn call_gemini(
    state: &AppState,
    message: &str,
    context: &str,
    intent_addon: &str,
    user_id: uuid::Uuid,
) -> Result<Json<AiResponse>, (StatusCode, Json<AiErrorResponse>)> {
    let system_prompt = build_system_prompt(intent_addon);

    match state.gemini.call(&system_prompt, message, context).await {
        Ok(text) => {
            tracing::info!(user_id = %user_id, status = "success", "AI response generated");
            Ok(Json(AiResponse { response: text }))
        }

        Err(GeminiError::UnexpectedResponse) => {
            tracing::error!(user_id = %user_id, "Gemini returned unexpected response format");
            Err((
                StatusCode::BAD_GATEWAY,
                Json(AiErrorResponse {
                    error: "AI service returned an unexpected response. Please try again."
                        .to_string(),
                }),
            ))
        }

        Err(GeminiError::Http(e)) => {
            tracing::error!(user_id = %user_id, error = %e, "Gemini HTTP request failed");
            Err((
                StatusCode::BAD_GATEWAY,
                Json(AiErrorResponse {
                    error: "Failed to reach AI service. Please try again later.".to_string(),
                }),
            ))
        }
    }
}
