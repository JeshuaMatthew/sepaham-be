use std::env;

/// Runtime configuration, loaded from environment variables (see `.env.example`).
#[derive(Debug, Clone)]
pub struct Config {
    pub database_url: String,
    pub jwt_secret: String,
    pub jwt_expiry_hours: i64,
    pub bind_addr: String,
    pub cors_allowed_origins: Vec<String>,
    /// Public base URL of this server, used to build absolute image URLs.
    pub public_base_url: String,
    /// LiveKit server URL the frontend connects to (ws://… or wss://…).
    pub livekit_url: String,
    pub livekit_api_key: String,
    pub livekit_api_secret: String,
}

impl Config {
    /// Read configuration from the environment. Panics with a clear message if a
    /// required variable is missing, since the app cannot run without it.
    pub fn from_env() -> Self {
        let database_url = env::var("DATABASE_URL")
            .expect("DATABASE_URL must be set (see backend/.env.example)");

        let jwt_secret = env::var("JWT_SECRET")
            .unwrap_or_else(|_| "dev-secret-change-me".to_string());

        let jwt_expiry_hours = env::var("JWT_EXPIRY_HOURS")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(72);

        let bind_addr =
            env::var("BIND_ADDR").unwrap_or_else(|_| "0.0.0.0:8080".to_string());

        let public_base_url = env::var("PUBLIC_BASE_URL")
            .unwrap_or_else(|_| "http://localhost:8080".to_string());

        // LiveKit dev defaults match `livekit-server --dev` (key=devkey/secret=secret).
        let livekit_url =
            env::var("LIVEKIT_URL").unwrap_or_else(|_| "ws://localhost:7880".to_string());
        let livekit_api_key =
            env::var("LIVEKIT_API_KEY").unwrap_or_else(|_| "devkey".to_string());
        let livekit_api_secret =
            env::var("LIVEKIT_API_SECRET").unwrap_or_else(|_| "secret".to_string());

        let cors_allowed_origins = env::var("CORS_ALLOWED_ORIGINS")
            .unwrap_or_else(|_| "http://localhost:5173,http://localhost:5174".to_string())
            .split(',')
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .collect();

        Self {
            database_url,
            jwt_secret,
            jwt_expiry_hours,
            bind_addr,
            cors_allowed_origins,
            public_base_url,
            livekit_url,
            livekit_api_key,
            livekit_api_secret,
        }
    }
}
