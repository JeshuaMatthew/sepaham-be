//! Abstraction layer between the application and the Gemini API.
//!
//! Handlers never call Gemini directly — they call `GeminiService`.
//! This keeps HTTP details, API key management, and response parsing
//! in one place and makes the handler unit-testable.

use reqwest::Client;

use crate::ai::models::{
    GeminiCandidate, GeminiContent, GeminiPart, GeminiRequest, GeminiResponse,
};
use crate::ai::prompt::SYSTEM_PROMPT;

/// Gemini REST endpoint — `generateContent` for the 3.6 flash model.
const GEMINI_API_URL: &str =
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent";

/// Errors that can occur when talking to Gemini.
#[derive(Debug, thiserror::Error)]
pub enum GeminiError {
    #[error("HTTP request to Gemini failed: {0}")]
    Http(#[from] reqwest::Error),

    #[error("Gemini returned an unexpected response format")]
    UnexpectedResponse,
}

/// Reusable service — one instance per application lifetime (stored in `AppState`).
#[derive(Clone)]
pub struct GeminiService {
    /// Shared HTTP client (connection-pool reuse across requests).
    client: Client,
    /// Gemini API key read from `GEMINI_API_KEY` env var.
    api_key: String,
}

impl GeminiService {
    /// Construct the service.
    /// Panics at startup if `GEMINI_API_KEY` is not set — fast-fail is
    /// intentional so misconfigurations surface immediately, not at runtime.
    pub fn new(api_key: String) -> Self {
        Self {
            client: Client::new(),
            api_key,
        }
    }

    /// Send `user_message` to Gemini without any database context.
    /// Useful for simple queries and testing.
    #[allow(dead_code)]
    pub async fn generate(&self, user_message: &str) -> Result<String, GeminiError> {
        self.generate_with_context(user_message, "").await
    }

    /// Like `generate`, but injects a `context` block (database snapshot)
    /// between the system instruction and the user message.
    /// Uses the base `SYSTEM_PROMPT`.
    pub async fn generate_with_context(
        &self,
        user_message: &str,
        context: &str,
    ) -> Result<String, GeminiError> {
        self.call(SYSTEM_PROMPT, user_message, context).await
    }

    /// Full control — caller provides a custom `system_prompt` (e.g. base + intent addon),
    /// optional DB `context`, and the `user_message`.
    ///
    /// Prompt layout sent to Gemini:
    /// ```text
    /// [system_prompt]          ← base + intent-specific instructions
    /// [context block]          ← Sepaham DB data (source of truth)
    /// [user message]           ← actual question
    /// ```
    pub async fn call(
        &self,
        system_prompt: &str,
        user_message: &str,
        context: &str,
    ) -> Result<String, GeminiError> {
        let url = format!("{}?key={}", GEMINI_API_URL, self.api_key);

        let user_text = if context.is_empty() {
            user_message.to_string()
        } else {
            format!("{}\n\n## User Question\n{}", context, user_message)
        };

        let payload = GeminiRequest {
            system_instruction: GeminiContent {
                parts: vec![GeminiPart {
                    text: system_prompt.to_string(),
                }],
            },
            contents: vec![GeminiContent {
                parts: vec![GeminiPart { text: user_text }],
            }],
        };

        let raw = self
            .client
            .post(&url)
            .json(&payload)
            .send()
            .await?;

        let status = raw.status();
        let body_text = raw.text().await.unwrap_or_default();

        tracing::debug!(gemini_status = %status, gemini_body = %body_text, "Raw Gemini response");

        if !status.is_success() {
            tracing::error!(gemini_status = %status, gemini_body = %body_text, "Gemini API error");
            return Err(GeminiError::UnexpectedResponse);
        }

        let response: GeminiResponse = serde_json::from_str(&body_text)
            .map_err(|e| {
                tracing::error!(parse_error = %e, body = %body_text, "Failed to parse Gemini response");
                GeminiError::UnexpectedResponse
            })?;

        // Walk the response tree: candidates[0].content.parts[0].text
        let text = response
            .candidates
            .and_then(|mut c: Vec<GeminiCandidate>| {
                if c.is_empty() {
                    None
                } else {
                    c.remove(0).content
                }
            })
            .and_then(|content: GeminiContent| content.parts.into_iter().next())
            .map(|part: GeminiPart| part.text)
            .ok_or(GeminiError::UnexpectedResponse)?;

        Ok(text)
    }
}
