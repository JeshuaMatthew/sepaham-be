pub mod extractor;
pub mod handlers;
pub mod jwt;
pub mod models;
pub mod password;

use axum::routing::{get, post};
use axum::Router;

use crate::state::AppState;

/// Routes mounted under `/api/auth`.
pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/register", post(handlers::register))
        .route("/login", post(handlers::login))
        .route("/me", get(handlers::me))
}
