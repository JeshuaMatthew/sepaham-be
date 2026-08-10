mod auth;
mod catalog;
mod chat;
mod collab;
mod community;
mod config;
mod db;
mod error;
mod faculty;
mod github;
mod images;
mod profile;
mod roadmap;
mod router;
mod state;

use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

use crate::config::Config;
use crate::state::AppState;

#[tokio::main]
async fn main() {
    // Load .env if present (ignored in production where real env vars are set).
    dotenvy::dotenv().ok();

    tracing_subscriber::registry()
        .with(EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")))
        .with(tracing_subscriber::fmt::layer())
        .init();

    let config = Config::from_env();

    let pool = db::connect(&config.database_url)
        .await
        .expect("failed to connect to Postgres — is the database running?");

    db::migrate(&pool).await.expect("failed to run migrations");
    tracing::info!("migrations up to date");

    // Ensure the uploads directory exists for stored (WebP) images.
    tokio::fs::create_dir_all(images::UPLOADS_DIR)
        .await
        .expect("failed to create uploads dir");

    let bind_addr = config.bind_addr.clone();
    let state = AppState::new(pool, config);
    let app = router::build(state);

    let listener = tokio::net::TcpListener::bind(&bind_addr)
        .await
        .unwrap_or_else(|_| panic!("failed to bind to {bind_addr}"));

    tracing::info!("Sepaham backend listening on http://{bind_addr}");

    axum::serve(listener, app)
        .await
        .expect("server error");
}
