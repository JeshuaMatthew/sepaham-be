//! Request and response types for the AI endpoints.
//! No business logic here — only data shapes.

use serde::{Deserialize, Serialize};

/// Maximum allowed length (bytes) for a user message sent to AI.
pub const MAX_MESSAGE_LEN: usize = 2_000;

// ---------------------------------------------------------------------------
// Intent — describes what kind of help the user is asking for
// ---------------------------------------------------------------------------

/// The type of AI assistance the user is requesting.
///
/// Used by `POST /api/ai/assist` to select the right prompt template
/// and the right context sections from the database.
#[derive(Debug, Deserialize, Clone, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum AiIntent {
    /// "Jurusan / role apa yang cocok untuk saya?"
    RecommendRole,
    /// "Jelaskan roadmap X" / "Bagaimana cara belajar Y?"
    ExplainRoadmap,
    /// "Apa prospek karir jurusan ini?" / "Bagaimana jalan karir seorang backend engineer?"
    CareerPath,
    /// "Cari magang / internship yang cocok untuk saya"
    FindInternship,
    /// Catch-all for questions that don't match a specific intent
    #[serde(other)]
    General,
}

// ---------------------------------------------------------------------------
// Phase 2 — general generate endpoint
// ---------------------------------------------------------------------------

/// Body accepted by `POST /api/ai/generate`.
#[derive(Debug, Deserialize)]
pub struct AiRequest {
    pub message: String,
}

/// Body returned by both AI endpoints on success.
#[derive(Debug, Serialize)]
pub struct AiResponse {
    pub response: String,
}

/// Generic error body returned to the client.
#[derive(Debug, Serialize)]
pub struct AiErrorResponse {
    pub error: String,
}

// ---------------------------------------------------------------------------
// Phase 3 — intent-aware assist endpoint
// ---------------------------------------------------------------------------

/// Body accepted by `POST /api/ai/assist`.
///
/// Example:
/// ```json
/// {
///   "intent": "recommend_role",
///   "message": "Saya suka matematika dan coding, cocoknya jadi apa?"
/// }
/// ```
#[derive(Debug, Deserialize)]
pub struct AiAssistRequest {
    /// What kind of help the user wants. Defaults to `general` if omitted.
    #[serde(default = "default_intent")]
    pub intent: AiIntent,
    /// The user's actual question or message.
    pub message: String,
}

fn default_intent() -> AiIntent {
    AiIntent::General
}

// ---------------------------------------------------------------------------
// GET /api/ai/feed — home feed response types
// ---------------------------------------------------------------------------

/// A single developer quote returned in the feed.
#[derive(Debug, Serialize)]
pub struct DevQuote {
    pub text: String,
    pub author: String,
}

/// GitHub activity nudge shown in the home sidebar.
#[derive(Debug, Serialize)]
pub struct GithubNudge {
    pub title: String,
    pub message: String,
    pub streak: i32,
    pub cta: String,
}

/// An internship suggestion from `ai_internships`.
#[derive(Debug, Serialize)]
pub struct AiFeedInternship {
    pub id: String,
    pub company: String,
    pub emoji: String,
    pub role: String,
    pub location: String,
    #[serde(rename = "type")]
    pub kind: String,
    #[serde(rename = "matchPercent")]
    pub match_percent: i32,
    pub tags: Vec<String>,
}

/// Top-level response body for `GET /api/ai/feed`.
#[derive(Debug, Serialize)]
pub struct AiFeedResponse {
    pub quotes: Vec<DevQuote>,
    pub nudge: GithubNudge,
    pub internships: Vec<AiFeedInternship>,
}

// ---------------------------------------------------------------------------
// Gemini API wire types (used only inside `service.rs`)
// ---------------------------------------------------------------------------

/// Top-level request payload sent to `generateContent`.
#[derive(Debug, Serialize)]
pub struct GeminiRequest {
    pub system_instruction: GeminiContent,
    pub contents: Vec<GeminiContent>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct GeminiContent {
    pub parts: Vec<GeminiPart>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct GeminiPart {
    pub text: String,
}

/// Top-level response from `generateContent`.
#[derive(Debug, Deserialize)]
pub struct GeminiResponse {
    pub candidates: Option<Vec<GeminiCandidate>>,
}

#[derive(Debug, Deserialize)]
pub struct GeminiCandidate {
    pub content: Option<GeminiContent>,
}
