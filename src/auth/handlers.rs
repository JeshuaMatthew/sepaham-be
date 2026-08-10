use axum::extract::State;
use axum::http::StatusCode;
use axum::Json;

use crate::auth::extractor::AuthUser;
use crate::auth::jwt::create_token;
use crate::auth::models::{
    AuthResponse, LoginRequest, RegisterRequest, User, UserDto, UserRole,
};
use crate::auth::password::{hash_password, verify_password};
use crate::error::{AppError, AppResult};
use crate::state::AppState;

/// POST /api/auth/register — create a new account and return a JWT.
pub async fn register(
    State(state): State<AppState>,
    Json(req): Json<RegisterRequest>,
) -> AppResult<(StatusCode, Json<AuthResponse>)> {
    let email = req.email.trim().to_lowercase();
    let name = req.name.trim().to_string();

    if !email.contains('@') {
        return Err(AppError::BadRequest("invalid email format".into()));
    }
    if req.password.len() < 6 {
        return Err(AppError::BadRequest(
            "password must be at least 6 characters".into(),
        ));
    }
    if name.is_empty() {
        return Err(AppError::BadRequest("name is required".into()));
    }

    let role = req.role.unwrap_or(UserRole::Student);
    let password_hash = hash_password(&req.password)?;

    let mut tx = state.pool.begin().await?;

    let user = sqlx::query_as::<_, User>(
        r#"
        INSERT INTO users (email, password_hash, role, name)
        VALUES ($1, $2, $3, $4)
        RETURNING id, email, password_hash, role, name, created_at, updated_at
        "#,
    )
    .bind(&email)
    .bind(&password_hash)
    .bind(role)
    .bind(&name)
    .fetch_one(&mut *tx)
    .await
    .map_err(|e| {
        if let sqlx::Error::Database(db) = &e {
            if db.is_unique_violation() {
                return AppError::Conflict("email is already registered".into());
            }
        }
        AppError::Database(e)
    })?;

    // Every user gets an (empty) profile row up front.
    sqlx::query("INSERT INTO profiles (user_id) VALUES ($1)")
        .bind(user.id)
        .execute(&mut *tx)
        .await?;

    tx.commit().await?;

    let token = create_token(
        user.id,
        user.role,
        &state.config.jwt_secret,
        state.config.jwt_expiry_hours,
    )?;

    Ok((
        StatusCode::CREATED,
        Json(AuthResponse {
            token,
            user: UserDto::from_user(&user, true),
        }),
    ))
}

/// POST /api/auth/login — verify credentials and return a JWT.
pub async fn login(
    State(state): State<AppState>,
    Json(req): Json<LoginRequest>,
) -> AppResult<Json<AuthResponse>> {
    let email = req.email.trim().to_lowercase();

    let user = sqlx::query_as::<_, User>(
        r#"
        SELECT id, email, password_hash, role, name, created_at, updated_at
        FROM users
        WHERE email = $1
        "#,
    )
    .bind(&email)
    .fetch_optional(&state.pool)
    .await?
    .ok_or(AppError::Unauthorized)?;

    if !verify_password(&req.password, &user.password_hash) {
        return Err(AppError::Unauthorized);
    }

    let token = create_token(
        user.id,
        user.role,
        &state.config.jwt_secret,
        state.config.jwt_expiry_hours,
    )?;

    Ok(Json(AuthResponse {
        token,
        user: UserDto::from_user(&user, false),
    }))
}

/// GET /api/auth/me — return the current authenticated user.
pub async fn me(
    State(state): State<AppState>,
    auth: AuthUser,
) -> AppResult<Json<UserDto>> {
    let user = sqlx::query_as::<_, User>(
        r#"
        SELECT id, email, password_hash, role, name, created_at, updated_at
        FROM users
        WHERE id = $1
        "#,
    )
    .bind(auth.id)
    .fetch_optional(&state.pool)
    .await?
    .ok_or(AppError::Unauthorized)?;

    Ok(Json(UserDto::from_user(&user, false)))
}
