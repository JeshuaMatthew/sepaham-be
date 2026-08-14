//! AI module — Gemini integration for Sepaham.
//!
//! Structure:
//! - `models`  : request/response structs
//! - `prompt`  : system instructions & prompt templates
//! - `service` : HTTP abstraction over Gemini API
//! - `handler` : Axum route handlers
//! - `context` : (Phase 2) database context builder

pub mod context;
pub mod handler;
pub mod models;
pub mod prompt;
pub mod service;

use axum::routing::{get, post};
use axum::Router;

use crate::state::AppState;

/// Mount all AI routes under `/ai`.
/// Registered in the main router as `.nest("/ai", ai::routes())`.
///
/// | Method | Path            | Description                              |
/// |--------|-----------------|------------------------------------------|
/// | GET    | /ai/feed        | Home feed: quote, nudge, internships     |
/// | POST   | /ai/generate    | General AI with full DB context          |
/// | POST   | /ai/assist      | Intent-aware AI (career, roadmap, etc.)  |
pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/feed", get(handler::feed))
        .route("/generate", post(handler::generate))
        .route("/assist", post(handler::assist))
}
