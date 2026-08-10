//! Collab ("Cari Tim"): project-team requests, applicants, and the creator's
//! "My teams" view. Creating a request can also spin up a new team community.

use axum::extract::{Path, State};
use axum::http::StatusCode;
use axum::routing::{delete, get, patch, post};
use axum::{Json, Router};
use serde::Deserialize;
use serde_json::{json, Value};
use uuid::Uuid;

use crate::auth::extractor::AuthUser;
use crate::error::{AppError, AppResult};
use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/collab/requests", get(list_requests).post(create_request))
        .route("/collab/requests/{id}", delete(delete_request))
        .route("/collab/my-teams", get(my_teams))
        .route("/collab/requests/{id}/apply", post(apply))
        .route(
            "/collab/requests/{id}/applicants/{applicant_id}",
            patch(set_applicant_status),
        )
}

/// Shared SELECT for a collab request in the shape the frontend expects.
/// Callers append their own WHERE/ORDER clause.
pub(crate) const REQUEST_SELECT: &str = "
    SELECT c.id, c.title, c.description, c.needed_roles, c.tech_stack, c.tags,
           c.repo_url,
           ARRAY(SELECT url FROM collab_request_images i
                 WHERE i.request_id = c.id ORDER BY i.sort_order) AS images,
           c.community_id, s.name AS community_name,
           c.author_name, c.author_avatar, c.author_role,
           c.members_current, c.members_needed,
           (SELECT count(*) FROM collab_applicants a WHERE a.request_id = c.id) AS interested,
           c.status::text AS status, c.closed,
           FLOOR(EXTRACT(EPOCH FROM (now() - c.created_at)) / 60)::bigint AS posted_minutes_ago
    FROM collab_requests c
    LEFT JOIN servers s ON s.id = c.community_id
";

#[derive(sqlx::FromRow)]
pub(crate) struct CollabRow {
    id: Uuid,
    title: String,
    description: String,
    needed_roles: Vec<String>,
    tech_stack: Vec<String>,
    tags: Vec<String>,
    repo_url: Option<String>,
    images: Vec<String>,
    community_id: Option<String>,
    community_name: Option<String>,
    author_name: String,
    author_avatar: String,
    author_role: String,
    members_current: i32,
    members_needed: i32,
    interested: i64,
    status: String,
    pub(crate) closed: bool,
    posted_minutes_ago: i64,
}

impl CollabRow {
    pub(crate) fn id(&self) -> Uuid {
        self.id
    }
}

pub(crate) fn request_json(r: &CollabRow) -> Value {
    json!({
        "id": r.id,
        "title": r.title,
        "description": r.description,
        "neededRoles": r.needed_roles,
        "techStack": r.tech_stack,
        "tags": r.tags,
        "repoUrl": r.repo_url,
        "images": r.images,
        "communityId": r.community_id,
        "communityName": r.community_name,
        "author": {
            "name": r.author_name,
            "avatar": r.author_avatar,
            "role": r.author_role,
        },
        "membersCurrent": r.members_current,
        "membersNeeded": r.members_needed,
        "interested": r.interested,
        "status": r.status,
        "postedMinutesAgo": r.posted_minutes_ago,
    })
}

#[derive(sqlx::FromRow)]
struct ApplicantRow {
    id: Uuid,
    request_id: Uuid,
    name: String,
    avatar: String,
    role: String,
    message: Option<String>,
    status: String,
    applied_minutes_ago: i64,
}

fn applicant_json(a: &ApplicantRow) -> Value {
    json!({
        "id": a.id,
        "name": a.name,
        "avatar": a.avatar,
        "role": a.role,
        "message": a.message,
        "status": a.status,
        "appliedMinutesAgo": a.applied_minutes_ago,
    })
}

#[derive(sqlx::FromRow)]
struct AuthorInfo {
    name: String,
    avatar: String,
    role: String,
}

async fn author_info(state: &AppState, user_id: Uuid) -> AppResult<AuthorInfo> {
    Ok(sqlx::query_as::<_, AuthorInfo>(
        "SELECT u.name, COALESCE(p.avatar_url, '') AS avatar, COALESCE(p.role_title, '') AS role
         FROM users u LEFT JOIN profiles p ON p.user_id = u.id WHERE u.id = $1",
    )
    .bind(user_id)
    .fetch_one(&state.pool)
    .await?)
}

fn initials(name: &str) -> String {
    let words: Vec<&str> = name.split_whitespace().collect();
    let pick = |w: &str| w.chars().next().map(|c| c.to_ascii_uppercase()).unwrap_or('T');
    match words.as_slice() {
        [a, b, ..] => format!("{}{}", pick(a), pick(b)),
        [a] => a.chars().take(2).collect::<String>().to_uppercase(),
        _ => "TM".to_string(),
    }
}

// ---------------------------------------------------------------------------
// GET /api/collab/requests — all open requests (public)
// ---------------------------------------------------------------------------
async fn list_requests(State(state): State<AppState>) -> AppResult<Json<Value>> {
    let sql = format!("{REQUEST_SELECT} WHERE NOT c.closed ORDER BY c.created_at DESC");
    let rows = sqlx::query_as::<_, CollabRow>(&sql).fetch_all(&state.pool).await?;
    let requests: Vec<Value> = rows.iter().map(request_json).collect();
    Ok(Json(json!({ "requests": requests })))
}

// ---------------------------------------------------------------------------
// POST /api/collab/requests — create a request (+ optional new community)
// ---------------------------------------------------------------------------
#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct CreateCollabInput {
    title: String,
    #[serde(default)]
    description: String,
    #[serde(default)]
    needed_roles: Vec<String>,
    #[serde(default)]
    tech_stack: Vec<String>,
    #[serde(default)]
    tags: Vec<String>,
    repo_url: Option<String>,
    #[serde(default = "default_members")]
    members_needed: i32,
    #[serde(default)]
    images: Vec<String>,
    community_id: Option<String>,
    new_community_name: Option<String>,
}

fn default_members() -> i32 {
    2
}

async fn create_request(
    State(state): State<AppState>,
    auth: AuthUser,
    Json(input): Json<CreateCollabInput>,
) -> AppResult<(StatusCode, Json<Value>)> {
    if input.title.trim().is_empty() {
        return Err(AppError::BadRequest("title is required".into()));
    }
    let author = author_info(&state, auth.id).await?;

    let mut tx = state.pool.begin().await?;

    // Resolve the community: use an existing one, or create a fresh team community.
    let community_id = match input.community_id.as_ref().filter(|s| !s.is_empty()) {
        Some(cid) => {
            let exists: Option<String> =
                sqlx::query_scalar("SELECT id FROM servers WHERE id = $1")
                    .bind(cid)
                    .fetch_optional(&mut *tx)
                    .await?;
            exists.ok_or_else(|| AppError::BadRequest("community not found".into()))?
        }
        None => {
            let sid = format!("tim-{}", &Uuid::new_v4().simple().to_string()[..8]);
            let cname = input
                .new_community_name
                .as_ref()
                .map(|s| s.trim())
                .filter(|s| !s.is_empty())
                .unwrap_or_else(|| input.title.trim())
                .to_string();

            sqlx::query(
                "INSERT INTO servers (id, name, initial, color, owner_id, is_team_community)
                 VALUES ($1, $2, $3, '#e5e5e5', $4, true)",
            )
            .bind(&sid)
            .bind(&cname)
            .bind(initials(&cname))
            .bind(auth.id)
            .execute(&mut *tx)
            .await?;

            sqlx::query(
                "INSERT INTO channels (id, server_id, name, topic, kind, sort_order) VALUES
                    ($1, $2, 'general',  $3, 'text', 1),
                    ($4, $2, 'progress', 'Update progres & to-do proyek', 'text', 2)",
            )
            .bind(format!("{sid}-general"))
            .bind(&sid)
            .bind(format!("Diskusi tim: {cname}"))
            .bind(format!("{sid}-progress"))
            .execute(&mut *tx)
            .await?;

            sqlx::query(
                "INSERT INTO server_members (server_id, user_id) VALUES ($1, $2)
                 ON CONFLICT DO NOTHING",
            )
            .bind(&sid)
            .bind(auth.id)
            .execute(&mut *tx)
            .await?;

            sid
        }
    };

    let members_needed = input.members_needed.max(2);

    let id: Uuid = sqlx::query_scalar(
        "INSERT INTO collab_requests
            (author_id, author_name, author_avatar, author_role, title, description,
             needed_roles, tech_stack, tags, repo_url, community_id, members_current,
             members_needed, status)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, 1, $12, 'open')
         RETURNING id",
    )
    .bind(auth.id)
    .bind(&author.name)
    .bind(&author.avatar)
    .bind(&author.role)
    .bind(input.title.trim())
    .bind(&input.description)
    .bind(&input.needed_roles)
    .bind(&input.tech_stack)
    .bind(&input.tags)
    .bind(input.repo_url.as_ref().map(|s| s.trim()))
    .bind(&community_id)
    .bind(members_needed)
    .fetch_one(&mut *tx)
    .await?;

    for (i, src) in input.images.iter().enumerate() {
        // Re-encode data-URL images to a stored WebP file; keep plain URLs as-is.
        let url = crate::images::store_maybe(&state.config.public_base_url, src).await?;
        sqlx::query("INSERT INTO collab_request_images (request_id, url, sort_order) VALUES ($1, $2, $3)")
            .bind(id)
            .bind(&url)
            .bind(i as i32)
            .execute(&mut *tx)
            .await?;
    }

    tx.commit().await?;

    let row = fetch_request(&state, id).await?;
    Ok((StatusCode::CREATED, Json(request_json(&row))))
}

async fn fetch_request(state: &AppState, id: Uuid) -> AppResult<CollabRow> {
    let sql = format!("{REQUEST_SELECT} WHERE c.id = $1");
    sqlx::query_as::<_, CollabRow>(&sql)
        .bind(id)
        .fetch_optional(&state.pool)
        .await?
        .ok_or_else(|| AppError::NotFound("request not found".into()))
}

// ---------------------------------------------------------------------------
// DELETE /api/collab/requests/{id} — owner deletes their request + its images
// ---------------------------------------------------------------------------
async fn delete_request(
    State(state): State<AppState>,
    auth: AuthUser,
    Path(id): Path<Uuid>,
) -> AppResult<StatusCode> {
    let author_id: Option<Uuid> =
        sqlx::query_scalar("SELECT author_id FROM collab_requests WHERE id = $1")
            .bind(id)
            .fetch_optional(&state.pool)
            .await?
            .ok_or_else(|| AppError::NotFound("request not found".into()))?;

    if author_id != Some(auth.id) {
        return Err(AppError::Forbidden);
    }

    // Grab image URLs before the cascade removes the rows.
    let urls: Vec<String> =
        sqlx::query_scalar("SELECT url FROM collab_request_images WHERE request_id = $1")
            .bind(id)
            .fetch_all(&state.pool)
            .await?;

    sqlx::query("DELETE FROM collab_requests WHERE id = $1")
        .bind(id)
        .execute(&state.pool)
        .await?;

    // Delete the stored files too.
    for url in &urls {
        crate::images::delete_file(url).await;
    }

    Ok(StatusCode::NO_CONTENT)
}

// ---------------------------------------------------------------------------
// GET /api/collab/my-teams — requests created by the user + their applicants
// ---------------------------------------------------------------------------
async fn my_teams(State(state): State<AppState>, auth: AuthUser) -> AppResult<Json<Value>> {
    let sql = format!("{REQUEST_SELECT} WHERE c.author_id = $1 ORDER BY c.created_at DESC");
    let rows = sqlx::query_as::<_, CollabRow>(&sql)
        .bind(auth.id)
        .fetch_all(&state.pool)
        .await?;

    let ids: Vec<Uuid> = rows.iter().map(|r| r.id).collect();

    let applicants = sqlx::query_as::<_, ApplicantRow>(
        "SELECT id, request_id, name, avatar, role, message, status::text AS status,
                FLOOR(EXTRACT(EPOCH FROM (now() - created_at)) / 60)::bigint AS applied_minutes_ago
         FROM collab_applicants WHERE request_id = ANY($1) ORDER BY created_at",
    )
    .bind(&ids)
    .fetch_all(&state.pool)
    .await?;

    let teams: Vec<Value> = rows
        .iter()
        .map(|r| {
            let team_applicants: Vec<Value> = applicants
                .iter()
                .filter(|a| a.request_id == r.id)
                .map(applicant_json)
                .collect();
            json!({
                "request": request_json(r),
                "applicants": team_applicants,
                "communityServerId": r.community_id,
            })
        })
        .collect();

    Ok(Json(json!({ "teams": teams })))
}

// ---------------------------------------------------------------------------
// POST /api/collab/requests/{id}/apply — apply to join a request
// ---------------------------------------------------------------------------
#[derive(Deserialize)]
struct ApplyInput {
    #[serde(default)]
    message: Option<String>,
}

async fn apply(
    State(state): State<AppState>,
    auth: AuthUser,
    Path(id): Path<Uuid>,
    Json(input): Json<ApplyInput>,
) -> AppResult<(StatusCode, Json<Value>)> {
    let author_id: Option<Option<Uuid>> =
        sqlx::query_scalar("SELECT author_id FROM collab_requests WHERE id = $1 AND NOT closed")
            .bind(id)
            .fetch_optional(&state.pool)
            .await?;
    let author_id = author_id.ok_or_else(|| AppError::NotFound("request not found".into()))?;

    if author_id == Some(auth.id) {
        return Err(AppError::BadRequest("cannot apply to your own request".into()));
    }

    let already: Option<Uuid> = sqlx::query_scalar(
        "SELECT id FROM collab_applicants WHERE request_id = $1 AND user_id = $2",
    )
    .bind(id)
    .bind(auth.id)
    .fetch_optional(&state.pool)
    .await?;
    if already.is_some() {
        return Err(AppError::Conflict("you have already applied".into()));
    }

    let author = author_info(&state, auth.id).await?;

    let applicant = sqlx::query_as::<_, ApplicantRow>(
        "INSERT INTO collab_applicants (request_id, user_id, name, avatar, role, message, status)
         VALUES ($1, $2, $3, $4, $5, $6, 'pending')
         RETURNING id, request_id, name, avatar, role, message, status::text AS status,
                   0::bigint AS applied_minutes_ago",
    )
    .bind(id)
    .bind(auth.id)
    .bind(&author.name)
    .bind(&author.avatar)
    .bind(&author.role)
    .bind(input.message.as_ref().map(|s| s.trim()))
    .fetch_one(&state.pool)
    .await?;

    Ok((StatusCode::CREATED, Json(applicant_json(&applicant))))
}

// ---------------------------------------------------------------------------
// PATCH /api/collab/requests/{id}/applicants/{applicant_id} — accept/reject
// ---------------------------------------------------------------------------
#[derive(Deserialize)]
struct StatusInput {
    status: String,
}

#[derive(sqlx::FromRow)]
struct RequestOwnership {
    author_id: Option<Uuid>,
    community_id: Option<String>,
}

async fn set_applicant_status(
    State(state): State<AppState>,
    auth: AuthUser,
    Path((id, applicant_id)): Path<(Uuid, Uuid)>,
    Json(input): Json<StatusInput>,
) -> AppResult<Json<Value>> {
    if input.status != "accepted" && input.status != "rejected" {
        return Err(AppError::BadRequest(
            "status must be 'accepted' or 'rejected'".into(),
        ));
    }

    let owner = sqlx::query_as::<_, RequestOwnership>(
        "SELECT author_id, community_id FROM collab_requests WHERE id = $1",
    )
    .bind(id)
    .fetch_optional(&state.pool)
    .await?
    .ok_or_else(|| AppError::NotFound("request not found".into()))?;

    if owner.author_id != Some(auth.id) {
        return Err(AppError::Forbidden);
    }

    let applicant: Option<(Option<Uuid>, String)> = sqlx::query_as(
        "SELECT user_id, status::text FROM collab_applicants WHERE id = $1 AND request_id = $2",
    )
    .bind(applicant_id)
    .bind(id)
    .fetch_optional(&state.pool)
    .await?;
    let (applicant_user_id, previous_status) =
        applicant.ok_or_else(|| AppError::NotFound("applicant not found".into()))?;

    let mut tx = state.pool.begin().await?;

    sqlx::query(
        "UPDATE collab_applicants SET status = $3::applicant_status
         WHERE id = $1 AND request_id = $2",
    )
    .bind(applicant_id)
    .bind(id)
    .bind(&input.status)
    .execute(&mut *tx)
    .await?;

    // Accepting a not-yet-accepted applicant: add them to the community + bump count.
    if input.status == "accepted" && previous_status != "accepted" {
        if let (Some(cid), Some(uid)) = (&owner.community_id, applicant_user_id) {
            sqlx::query(
                "INSERT INTO server_members (server_id, user_id) VALUES ($1, $2)
                 ON CONFLICT DO NOTHING",
            )
            .bind(cid)
            .bind(uid)
            .execute(&mut *tx)
            .await?;
        }

        sqlx::query(
            "UPDATE collab_requests SET
                members_current = LEAST(members_current + 1, members_needed),
                status = CASE WHEN members_current + 1 >= members_needed
                              THEN 'full'::collab_status ELSE status END,
                updated_at = now()
             WHERE id = $1",
        )
        .bind(id)
        .execute(&mut *tx)
        .await?;
    }

    tx.commit().await?;

    let updated = sqlx::query_as::<_, ApplicantRow>(
        "SELECT id, request_id, name, avatar, role, message, status::text AS status,
                FLOOR(EXTRACT(EPOCH FROM (now() - created_at)) / 60)::bigint AS applied_minutes_ago
         FROM collab_applicants WHERE id = $1",
    )
    .bind(applicant_id)
    .fetch_one(&state.pool)
    .await?;

    Ok(Json(applicant_json(&updated)))
}
