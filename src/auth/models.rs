use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Application role. Maps to the Postgres `user_role` enum.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, sqlx::Type)]
#[sqlx(type_name = "user_role", rename_all = "lowercase")]
#[serde(rename_all = "lowercase")]
pub enum UserRole {
    Student,
    Faculty,
}

impl UserRole {
    pub fn as_str(&self) -> &'static str {
        match self {
            UserRole::Student => "student",
            UserRole::Faculty => "faculty",
        }
    }
}

/// A row from the `users` table.
#[derive(Debug, Clone, sqlx::FromRow)]
pub struct User {
    pub id: Uuid,
    pub email: String,
    pub password_hash: String,
    pub role: UserRole,
    pub name: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

// ----- Request / response DTOs -----

#[derive(Debug, Deserialize)]
pub struct RegisterRequest {
    pub email: String,
    pub password: String,
    pub name: String,
    /// Optional; defaults to "student".
    #[serde(default)]
    pub role: Option<UserRole>,
}

#[derive(Debug, Deserialize)]
pub struct LoginRequest {
    pub email: String,
    pub password: String,
}

#[derive(Debug, Serialize)]
pub struct UserDto {
    pub id: Uuid,
    pub email: String,
    pub name: String,
    pub role: UserRole,
    #[serde(rename = "isNewUser")]
    pub is_new_user: bool,
}

impl UserDto {
    pub fn from_user(user: &User, is_new_user: bool) -> Self {
        Self {
            id: user.id,
            email: user.email.clone(),
            name: user.name.clone(),
            role: user.role,
            is_new_user,
        }
    }
}

#[derive(Debug, Serialize)]
pub struct AuthResponse {
    pub token: String,
    pub user: UserDto,
}
