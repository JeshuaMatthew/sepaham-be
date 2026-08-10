use std::sync::Arc;

use sqlx::PgPool;
use tokio::sync::broadcast;

use crate::config::Config;

/// Shared application state passed to every handler via `State`.
#[derive(Clone)]
pub struct AppState {
    pub pool: PgPool,
    pub config: Arc<Config>,
    /// Fan-out of chat events (JSON strings) to connected WebSocket clients.
    pub events: broadcast::Sender<String>,
}

impl AppState {
    pub fn new(pool: PgPool, config: Config) -> Self {
        let (events, _) = broadcast::channel(1024);
        Self {
            pool,
            config: Arc::new(config),
            events,
        }
    }
}
