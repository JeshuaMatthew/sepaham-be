//! Faculty-only endpoints: the student-progress dashboard (aggregated from real
//! data) and moderation (ban a community, close a collab request) persisted to
//! the DB.

use axum::extract::{Path, State};
use axum::routing::{get, post};
use axum::{Json, Router};
use serde_json::{json, Value};
use uuid::Uuid;

use crate::auth::extractor::FacultyUser;
use crate::collab;
use crate::error::{AppError, AppResult};
use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/faculty/students", get(list_students))
        .route("/faculty/servers", get(list_mod_servers))
        .route("/faculty/servers/{id}/ban", post(toggle_ban))
        .route("/faculty/requests", get(list_mod_requests))
        .route("/faculty/requests/{id}/close", post(toggle_close))
}

// ---------------------------------------------------------------------------
// Student progress dashboard (aggregated from real users)
// ---------------------------------------------------------------------------
#[derive(sqlx::FromRow)]
struct StudentRow {
    id: String,
    name: String,
    avatar: String,
    role: String,
    cv_file_name: Option<String>,
    cv_uploaded_at: Option<String>,
    roadmap_title: String,
    roadmap_total: i64,
    roadmap_completed: i64,
    gh_repos: i32,
    gh_commits: i32,
    gh_langs: Vec<String>,
    projects: i64,
}

async fn list_students(
    State(state): State<AppState>,
    _faculty: FacultyUser,
) -> AppResult<Json<Value>> {
    let rows = sqlx::query_as::<_, StudentRow>(
        "SELECT
            u.id::text AS id,
            u.name,
            COALESCE(p.avatar_url, '') AS avatar,
            COALESCE(p.role_title, '') AS role,
            p.cv_file_name,
            to_char(p.cv_uploaded_at, 'YYYY-MM-DD') AS cv_uploaded_at,
            COALESCE(rm.title, '') AS roadmap_title,
            COALESCE((SELECT count(*) FROM roadmap_nodes n WHERE n.roadmap_id = rm.id), 0) AS roadmap_total,
            COALESCE((SELECT count(*) FROM submissions s
                      WHERE s.user_id = u.id AND s.roadmap_id = rm.id AND s.done), 0) AS roadmap_completed,
            COALESCE(gs.public_repos, 0) AS gh_repos,
            COALESCE(gs.total_commits, 0) AS gh_commits,
            COALESCE(
                (SELECT array_agg(elem->>'name')
                 FROM jsonb_array_elements(gs.top_languages) elem),
                ARRAY[]::text[]
            ) AS gh_langs,
            (SELECT count(*) FROM collab_requests c WHERE c.author_id = u.id) AS projects
         FROM users u
         LEFT JOIN profiles p ON p.user_id = u.id
         LEFT JOIN user_preferences pref ON pref.user_id = u.id
         LEFT JOIN roadmaps rm ON rm.role_id = pref.role_id
         LEFT JOIN github_stats gs ON gs.user_id = u.id
         WHERE u.role = 'student'
         ORDER BY u.created_at",
    )
    .fetch_all(&state.pool)
    .await?;

    let students: Vec<Value> = rows
        .iter()
        .map(|r| {
            json!({
                "id": r.id,
                "name": r.name,
                "avatar": r.avatar,
                "role": r.role,
                "cvFileName": r.cv_file_name,
                "cvUploadedAt": r.cv_uploaded_at,
                "roadmap": {
                    "title": r.roadmap_title,
                    "completed": r.roadmap_completed,
                    "total": r.roadmap_total,
                },
                "github": {
                    "repos": r.gh_repos,
                    "commits": r.gh_commits,
                    "topLanguages": r.gh_langs,
                },
                "projects": r.projects,
            })
        })
        .collect();

    Ok(Json(json!({ "students": students })))
}

// ---------------------------------------------------------------------------
// Moderation: communities (ban)
// ---------------------------------------------------------------------------
#[derive(sqlx::FromRow)]
struct ServerBanRow {
    id: String,
    name: String,
    initial: String,
    color: String,
    banned: bool,
}

async fn list_mod_servers(
    State(state): State<AppState>,
    _faculty: FacultyUser,
) -> AppResult<Json<Value>> {
    let rows = sqlx::query_as::<_, ServerBanRow>(
        "SELECT id, name, initial, color, banned FROM servers ORDER BY created_at",
    )
    .fetch_all(&state.pool)
    .await?;

    let banned_ids: Vec<&String> = rows.iter().filter(|s| s.banned).map(|s| &s.id).collect();
    let servers: Vec<Value> = rows
        .iter()
        .map(|s| json!({ "id": s.id, "name": s.name, "initial": s.initial, "color": s.color }))
        .collect();

    Ok(Json(json!({ "servers": servers, "bannedIds": banned_ids })))
}

async fn toggle_ban(
    State(state): State<AppState>,
    faculty: FacultyUser,
    Path(id): Path<String>,
) -> AppResult<Json<Value>> {
    let banned: bool = sqlx::query_scalar(
        "UPDATE servers SET
            banned = NOT banned,
            banned_by = CASE WHEN NOT banned THEN $2 ELSE NULL END,
            banned_at = CASE WHEN NOT banned THEN now() ELSE NULL END
         WHERE id = $1
         RETURNING banned",
    )
    .bind(&id)
    .bind(faculty.0.id)
    .fetch_optional(&state.pool)
    .await?
    .ok_or_else(|| AppError::NotFound("community not found".into()))?;

    Ok(Json(json!({ "id": id, "banned": banned })))
}

// ---------------------------------------------------------------------------
// Moderation: collab requests (close)
// ---------------------------------------------------------------------------
async fn list_mod_requests(
    State(state): State<AppState>,
    _faculty: FacultyUser,
) -> AppResult<Json<Value>> {
    let sql = format!("{} ORDER BY c.created_at DESC", collab::REQUEST_SELECT);
    let rows = sqlx::query_as::<_, collab::CollabRow>(&sql)
        .fetch_all(&state.pool)
        .await?;

    let requests: Vec<Value> = rows.iter().map(collab::request_json).collect();
    let closed_ids: Vec<Uuid> = rows.iter().filter(|r| r.closed).map(|r| r.id()).collect();

    Ok(Json(json!({ "requests": requests, "closedIds": closed_ids })))
}

async fn toggle_close(
    State(state): State<AppState>,
    _faculty: FacultyUser,
    Path(id): Path<Uuid>,
) -> AppResult<Json<Value>> {
    let closed: bool = sqlx::query_scalar(
        "UPDATE collab_requests SET closed = NOT closed, updated_at = now()
         WHERE id = $1 RETURNING closed",
    )
    .bind(id)
    .fetch_optional(&state.pool)
    .await?
    .ok_or_else(|| AppError::NotFound("request not found".into()))?;

    Ok(Json(json!({ "id": id, "closed": closed })))
}
