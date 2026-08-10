use std::sync::Arc;

use sqlx::PgPool;

use crate::config::Config;

/// Shared application state passed to every handler via `State`.
#[derive(Clone)]
pub struct AppState {
    pub pool: PgPool,
    pub config: Arc<Config>,
}

impl AppState {
    pub fn new(pool: PgPool, config: Config) -> Self {
        Self {
            pool,
            config: Arc::new(config),
        }
    }
}
