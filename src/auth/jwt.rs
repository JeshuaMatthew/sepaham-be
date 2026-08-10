use chrono::{Duration, Utc};
use jsonwebtoken::{decode, encode, DecodingKey, EncodingKey, Header, Validation};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::auth::models::UserRole;
use crate::error::AppError;

/// JWT payload. `sub` is the user id, `role` the application role.
#[derive(Debug, Serialize, Deserialize)]
pub struct Claims {
    pub sub: String,
    pub role: String,
    pub exp: i64,
    pub iat: i64,
}

/// Sign a JWT for a user.
pub fn create_token(
    user_id: Uuid,
    role: UserRole,
    secret: &str,
    expiry_hours: i64,
) -> Result<String, AppError> {
    let now = Utc::now();
    let claims = Claims {
        sub: user_id.to_string(),
        role: role.as_str().to_string(),
        iat: now.timestamp(),
        exp: (now + Duration::hours(expiry_hours)).timestamp(),
    };

    encode(
        &Header::default(),
        &claims,
        &EncodingKey::from_secret(secret.as_bytes()),
    )
    .map_err(|e| AppError::Internal(format!("failed to sign token: {e}")))
}

/// Verify a JWT and return its claims. Any failure maps to Unauthorized.
pub fn verify_token(token: &str, secret: &str) -> Result<Claims, AppError> {
    decode::<Claims>(
        token,
        &DecodingKey::from_secret(secret.as_bytes()),
        &Validation::default(),
    )
    .map(|data| data.claims)
    .map_err(|_| AppError::Unauthorized)
}
