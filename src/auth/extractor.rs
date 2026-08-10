use axum::extract::FromRequestParts;
use axum::http::header::AUTHORIZATION;
use axum::http::request::Parts;
use uuid::Uuid;

use crate::auth::jwt::verify_token;
use crate::auth::models::UserRole;
use crate::error::AppError;
use crate::state::AppState;

/// Authenticated principal, extracted from the `Authorization: Bearer <jwt>`
/// header. Add it as a handler argument to require authentication.
#[derive(Debug, Clone)]
pub struct AuthUser {
    pub id: Uuid,
    pub role: UserRole,
}

impl FromRequestParts<AppState> for AuthUser {
    type Rejection = AppError;

    async fn from_request_parts(
        parts: &mut Parts,
        state: &AppState,
    ) -> Result<Self, Self::Rejection> {
        let header = parts
            .headers
            .get(AUTHORIZATION)
            .and_then(|value| value.to_str().ok())
            .ok_or(AppError::Unauthorized)?;

        let token = header
            .strip_prefix("Bearer ")
            .or_else(|| header.strip_prefix("bearer "))
            .ok_or(AppError::Unauthorized)?
            .trim();

        let claims = verify_token(token, &state.config.jwt_secret)?;

        let id = Uuid::parse_str(&claims.sub).map_err(|_| AppError::Unauthorized)?;
        let role = match claims.role.as_str() {
            "faculty" => UserRole::Faculty,
            _ => UserRole::Student,
        };

        Ok(AuthUser { id, role })
    }
}

/// Like [`AuthUser`], but rejects non-faculty with 403. Use as a handler
/// argument to restrict an endpoint to faculty (content editing, moderation).
#[derive(Debug, Clone)]
pub struct FacultyUser(pub AuthUser);

impl FromRequestParts<AppState> for FacultyUser {
    type Rejection = AppError;

    async fn from_request_parts(
        parts: &mut Parts,
        state: &AppState,
    ) -> Result<Self, Self::Rejection> {
        let user = AuthUser::from_request_parts(parts, state).await?;
        if user.role != UserRole::Faculty {
            return Err(AppError::Forbidden);
        }
        Ok(FacultyUser(user))
    }
}
