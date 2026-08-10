use axum::http::{header, HeaderValue, Method};
use axum::routing::get;
use axum::{Json, Router};
use serde_json::json;
use tower_http::cors::{AllowOrigin, CorsLayer};
use tower_http::services::ServeDir;
use tower_http::trace::TraceLayer;

use crate::images::UPLOADS_DIR;
use crate::state::AppState;
use crate::{
    auth, catalog, chat, collab, community, faculty, github, profile, realtime, roadmap,
};

/// Build the full application router with all routes and middleware.
pub fn build(state: AppState) -> Router {
    let cors = build_cors(&state.config.cors_allowed_origins);

    let api = Router::new()
        .nest("/auth", auth::routes())
        .merge(catalog::routes())
        .merge(profile::routes())
        .merge(roadmap::routes())
        .merge(collab::routes())
        .merge(community::routes())
        .merge(github::routes())
        .merge(chat::routes())
        .merge(faculty::routes())
        .merge(realtime::routes());

    Router::new()
        .route("/health", get(health))
        .nest("/api", api)
        // Serve stored WebP images (loaded cross-origin as <img src>, no CORS needed).
        .nest_service("/uploads", ServeDir::new(UPLOADS_DIR))
        .layer(TraceLayer::new_for_http())
        .layer(cors)
        .with_state(state)
}

/// Liveness probe.
async fn health() -> Json<serde_json::Value> {
    Json(json!({ "status": "ok" }))
}

fn build_cors(origins: &[String]) -> CorsLayer {
    let parsed: Vec<HeaderValue> = origins
        .iter()
        .filter_map(|origin| origin.parse().ok())
        .collect();

    CorsLayer::new()
        .allow_origin(AllowOrigin::list(parsed))
        .allow_methods([
            Method::GET,
            Method::POST,
            Method::PUT,
            Method::PATCH,
            Method::DELETE,
            Method::OPTIONS,
        ])
        .allow_headers([header::AUTHORIZATION, header::CONTENT_TYPE])
        .allow_credentials(true)
}
