//! Roadmaps: public catalog + tree reads, per-student submissions & activity,
//! and faculty authoring (save the full tree). Owns all `/roadmaps*` routes so
//! GET/PUT on the same path live in one router (no cross-merge conflicts).

use axum::extract::{Path, State};
use axum::routing::{get, post, put};
use axum::{Json, Router};
use serde::{Deserialize, Serialize};
use serde_json::{json, Map, Value};

use crate::auth::extractor::{AuthUser, FacultyUser};
use crate::error::AppResult;
use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/roadmaps", get(list_roadmaps))
        .route("/roadmaps/{id}", get(get_roadmap).put(save_roadmap))
        .route("/roadmaps/{id}/activity", post(mark_activity))
        .route("/roadmaps/{id}/submissions", get(get_submissions))
        .route(
            "/roadmaps/{id}/nodes/{node_key}/submission",
            put(save_submission),
        )
        .route("/roadmap-activity", get(list_activity))
}

// ===========================================================================
// Catalog (public)
// ===========================================================================
#[derive(Serialize, sqlx::FromRow)]
#[serde(rename_all = "camelCase")]
struct RoadmapSummaryDto {
    id: String,
    role_id: Option<String>,
    title: String,
    emoji: String,
    color: String,
    description: String,
    difficulty: String,
    match_tags: Vec<String>,
    author: String,
    total_nodes: i64,
}

async fn list_roadmaps(State(state): State<AppState>) -> AppResult<Json<Value>> {
    let roadmaps = sqlx::query_as::<_, RoadmapSummaryDto>(
        "SELECT r.id, r.role_id, r.title, r.emoji, r.color, r.description,
                r.difficulty::text AS difficulty, r.match_tags, r.author,
                (SELECT count(*) FROM roadmap_nodes n WHERE n.roadmap_id = r.id) AS total_nodes
         FROM roadmaps r ORDER BY r.created_at",
    )
    .fetch_all(&state.pool)
    .await?;
    Ok(Json(json!({ "roadmaps": roadmaps })))
}

// ===========================================================================
// Tree (public read)
// ===========================================================================
#[derive(Serialize, sqlx::FromRow)]
#[serde(rename_all = "camelCase")]
struct NodeDto {
    #[serde(rename = "id")]
    node_key: String,
    title: String,
    emoji: String,
    x: f64,
    y: f64,
    #[serde(rename = "group", skip_serializing_if = "Option::is_none")]
    group_name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    image: Option<String>,
    title_inside: bool,
    always_unlocked: bool,
    optional: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    article: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    submission: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    resources: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    missions: Option<Value>,
}

#[derive(Serialize, sqlx::FromRow)]
#[serde(rename_all = "camelCase")]
struct EdgeDto {
    #[serde(rename = "id")]
    edge_key: String,
    #[serde(rename = "source")]
    source_key: String,
    #[serde(rename = "target")]
    target_key: String,
    dashed: bool,
    optional: bool,
    animated: bool,
}

#[derive(sqlx::FromRow)]
struct RoadmapHead {
    role_id: Option<String>,
    title: String,
    emoji: String,
    author: String,
    style: Value,
}

async fn get_roadmap(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> AppResult<Json<Value>> {
    let head = sqlx::query_as::<_, RoadmapHead>(
        "SELECT role_id, title, emoji, author, style FROM roadmaps WHERE id = $1",
    )
    .bind(&id)
    .fetch_optional(&state.pool)
    .await?;

    let nodes = fetch_nodes(&state, &id).await?;
    let edges = fetch_edges(&state, &id).await?;

    let (role_id, title, emoji, author, style) = match head {
        Some(h) => (h.role_id, h.title, h.emoji, h.author, h.style),
        None => (None, id.clone(), String::new(), String::new(), json!({})),
    };

    Ok(Json(json!({
        "id": id,
        "roleId": role_id,
        "title": title,
        "emoji": emoji,
        "author": author,
        "style": style,
        "nodes": nodes,
        "edges": edges,
    })))
}

async fn fetch_nodes(state: &AppState, id: &str) -> AppResult<Vec<NodeDto>> {
    Ok(sqlx::query_as::<_, NodeDto>(
        "SELECT node_key, title, emoji, x, y, group_name, image, title_inside,
                always_unlocked, optional, article, submission, resources, missions
         FROM roadmap_nodes WHERE roadmap_id = $1 ORDER BY sort_order",
    )
    .bind(id)
    .fetch_all(&state.pool)
    .await?)
}

async fn fetch_edges(state: &AppState, id: &str) -> AppResult<Vec<EdgeDto>> {
    Ok(sqlx::query_as::<_, EdgeDto>(
        "SELECT edge_key, source_key, target_key, dashed, optional, animated
         FROM roadmap_edges WHERE roadmap_id = $1",
    )
    .bind(id)
    .fetch_all(&state.pool)
    .await?)
}

// ===========================================================================
// Tree save (faculty) — upsert meta + replace nodes/edges
// ===========================================================================
#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct NodeInput {
    id: String,
    title: String,
    #[serde(default)]
    emoji: String,
    #[serde(default)]
    x: f64,
    #[serde(default)]
    y: f64,
    group: Option<String>,
    image: Option<String>,
    #[serde(default)]
    title_inside: bool,
    #[serde(default)]
    always_unlocked: bool,
    #[serde(default)]
    optional: bool,
    article: Option<String>,
    submission: Option<Value>,
    resources: Option<Value>,
    missions: Option<Value>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct EdgeInput {
    id: String,
    source: String,
    target: String,
    #[serde(default)]
    dashed: bool,
    #[serde(default)]
    optional: bool,
    #[serde(default)]
    animated: bool,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct SaveRoadmapInput {
    role_id: Option<String>,
    title: Option<String>,
    emoji: Option<String>,
    color: Option<String>,
    description: Option<String>,
    difficulty: Option<String>,
    match_tags: Option<Vec<String>>,
    author: Option<String>,
    style: Option<Value>,
    nodes: Option<Vec<NodeInput>>,
    edges: Option<Vec<EdgeInput>>,
}

async fn save_roadmap(
    State(state): State<AppState>,
    _faculty: FacultyUser,
    Path(id): Path<String>,
    Json(input): Json<SaveRoadmapInput>,
) -> AppResult<Json<Value>> {
    let mut tx = state.pool.begin().await?;

    // Upsert roadmap meta. Provided fields overwrite; omitted ones keep existing
    // (or take a sensible default on first insert).
    sqlx::query(
        "INSERT INTO roadmaps
            (id, role_id, title, emoji, color, description, difficulty, match_tags, author, style)
         VALUES ($1, $2, COALESCE($3, $1), COALESCE($4, ''), COALESCE($5, ''),
                 COALESCE($6, ''), COALESCE($7::roadmap_difficulty, 'Beginner'),
                 COALESCE($8, '{}'::text[]), COALESCE($9, ''), COALESCE($10, '{}'::jsonb))
         ON CONFLICT (id) DO UPDATE SET
            role_id     = COALESCE($2, roadmaps.role_id),
            title       = COALESCE($3, roadmaps.title),
            emoji       = COALESCE($4, roadmaps.emoji),
            color       = COALESCE($5, roadmaps.color),
            description = COALESCE($6, roadmaps.description),
            difficulty  = COALESCE($7::roadmap_difficulty, roadmaps.difficulty),
            match_tags  = COALESCE($8, roadmaps.match_tags),
            author      = COALESCE($9, roadmaps.author),
            style       = COALESCE($10, roadmaps.style),
            updated_at  = now()",
    )
    .bind(&id)
    .bind(&input.role_id)
    .bind(&input.title)
    .bind(&input.emoji)
    .bind(&input.color)
    .bind(&input.description)
    .bind(&input.difficulty)
    .bind(&input.match_tags)
    .bind(&input.author)
    .bind(&input.style)
    .execute(&mut *tx)
    .await?;

    // Image files to remove after commit (old node images no longer referenced).
    let mut images_to_delete: Vec<String> = Vec::new();

    if let Some(nodes) = &input.nodes {
        let old_images: Vec<String> = sqlx::query_scalar(
            "SELECT image FROM roadmap_nodes WHERE roadmap_id = $1 AND image IS NOT NULL",
        )
        .bind(&id)
        .fetch_all(&mut *tx)
        .await?;

        sqlx::query("DELETE FROM roadmap_nodes WHERE roadmap_id = $1")
            .bind(&id)
            .execute(&mut *tx)
            .await?;

        let mut new_images: std::collections::HashSet<String> = std::collections::HashSet::new();
        for (i, n) in nodes.iter().enumerate() {
            // Re-encode data-URL images to a stored WebP; keep existing URLs as-is.
            let image = match &n.image {
                Some(src) => Some(crate::images::store_maybe(&state.config.public_base_url, src).await?),
                None => None,
            };
            if let Some(url) = &image {
                new_images.insert(url.clone());
            }
            sqlx::query(
                "INSERT INTO roadmap_nodes
                    (roadmap_id, node_key, title, emoji, x, y, group_name, image,
                     title_inside, always_unlocked, optional, article, submission,
                     resources, missions, sort_order)
                 VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)",
            )
            .bind(&id)
            .bind(&n.id)
            .bind(&n.title)
            .bind(&n.emoji)
            .bind(n.x)
            .bind(n.y)
            .bind(&n.group)
            .bind(&image)
            .bind(n.title_inside)
            .bind(n.always_unlocked)
            .bind(n.optional)
            .bind(&n.article)
            .bind(&n.submission)
            .bind(&n.resources)
            .bind(&n.missions)
            .bind(i as i32)
            .execute(&mut *tx)
            .await?;
        }

        // Old images dropped from the new set get their files deleted (post-commit).
        for old in old_images {
            if !new_images.contains(&old) {
                images_to_delete.push(old);
            }
        }
    }

    if let Some(edges) = &input.edges {
        sqlx::query("DELETE FROM roadmap_edges WHERE roadmap_id = $1")
            .bind(&id)
            .execute(&mut *tx)
            .await?;
        for e in edges {
            sqlx::query(
                "INSERT INTO roadmap_edges
                    (roadmap_id, edge_key, source_key, target_key, dashed, optional, animated)
                 VALUES ($1,$2,$3,$4,$5,$6,$7)",
            )
            .bind(&id)
            .bind(&e.id)
            .bind(&e.source)
            .bind(&e.target)
            .bind(e.dashed)
            .bind(e.optional)
            .bind(e.animated)
            .execute(&mut *tx)
            .await?;
        }
    }

    tx.commit().await?;

    for url in &images_to_delete {
        crate::images::delete_file(url).await;
    }

    Ok(Json(json!({ "id": id, "ok": true })))
}

// ===========================================================================
// Student submissions (per node)
// ===========================================================================
#[derive(sqlx::FromRow)]
struct SubmissionRow {
    node_key: String,
    done: bool,
    file_name: Option<String>,
    text_answer: Option<String>,
    score: Option<i32>,
    quiz_answers: Option<Value>,
}

fn submission_state(
    done: bool,
    file_name: &Option<String>,
    text_answer: &Option<String>,
    score: Option<i32>,
    quiz_answers: &Option<Value>,
) -> Value {
    let mut o = Map::new();
    o.insert("done".into(), json!(done));
    if let Some(f) = file_name {
        o.insert("fileName".into(), json!(f));
    }
    if let Some(t) = text_answer {
        o.insert("text".into(), json!(t));
    }
    if let Some(s) = score {
        o.insert("score".into(), json!(s));
    }
    if let Some(q) = quiz_answers {
        o.insert("quizAnswers".into(), q.clone());
    }
    Value::Object(o)
}

/// Returns `{ [nodeKey]: SubmissionState }` for the current user + roadmap.
async fn get_submissions(
    State(state): State<AppState>,
    auth: AuthUser,
    Path(id): Path<String>,
) -> AppResult<Json<Value>> {
    let rows = sqlx::query_as::<_, SubmissionRow>(
        "SELECT node_key, done, file_name, text_answer, score, quiz_answers
         FROM submissions WHERE user_id = $1 AND roadmap_id = $2",
    )
    .bind(auth.id)
    .bind(&id)
    .fetch_all(&state.pool)
    .await?;

    let mut map = Map::new();
    for r in &rows {
        map.insert(
            r.node_key.clone(),
            submission_state(r.done, &r.file_name, &r.text_answer, r.score, &r.quiz_answers),
        );
    }
    Ok(Json(Value::Object(map)))
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct SubmissionInput {
    #[serde(default)]
    done: bool,
    file_name: Option<String>,
    text: Option<String>,
    score: Option<i32>,
    quiz_answers: Option<Value>,
}

async fn save_submission(
    State(state): State<AppState>,
    auth: AuthUser,
    Path((id, node_key)): Path<(String, String)>,
    Json(input): Json<SubmissionInput>,
) -> AppResult<Json<Value>> {
    let row = sqlx::query_as::<_, SubmissionRow>(
        "INSERT INTO submissions
            (user_id, roadmap_id, node_key, done, file_name, text_answer, score, quiz_answers)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
         ON CONFLICT (user_id, roadmap_id, node_key) DO UPDATE SET
            done = EXCLUDED.done, file_name = EXCLUDED.file_name,
            text_answer = EXCLUDED.text_answer, score = EXCLUDED.score,
            quiz_answers = EXCLUDED.quiz_answers, updated_at = now()
         RETURNING node_key, done, file_name, text_answer, score, quiz_answers",
    )
    .bind(auth.id)
    .bind(&id)
    .bind(&node_key)
    .bind(input.done)
    .bind(&input.file_name)
    .bind(&input.text)
    .bind(input.score)
    .bind(&input.quiz_answers)
    .fetch_one(&state.pool)
    .await?;

    Ok(Json(submission_state(
        row.done,
        &row.file_name,
        &row.text_answer,
        row.score,
        &row.quiz_answers,
    )))
}

// ===========================================================================
// Roadmap activity (recently opened/worked)
// ===========================================================================
async fn mark_activity(
    State(state): State<AppState>,
    auth: AuthUser,
    Path(id): Path<String>,
) -> AppResult<Json<Value>> {
    sqlx::query(
        "INSERT INTO roadmap_activity (user_id, roadmap_id, last_active_at)
         VALUES ($1, $2, now())
         ON CONFLICT (user_id, roadmap_id) DO UPDATE SET last_active_at = now()",
    )
    .bind(auth.id)
    .bind(&id)
    .execute(&state.pool)
    .await?;
    Ok(Json(json!({ "ok": true })))
}

#[derive(sqlx::FromRow)]
struct ActivityRow {
    roadmap_id: String,
    ts: i64,
}

/// Returns `{ [roadmapId]: epochMillis }` for the current user.
async fn list_activity(
    State(state): State<AppState>,
    auth: AuthUser,
) -> AppResult<Json<Value>> {
    let rows = sqlx::query_as::<_, ActivityRow>(
        "SELECT roadmap_id, (EXTRACT(EPOCH FROM last_active_at) * 1000)::bigint AS ts
         FROM roadmap_activity WHERE user_id = $1",
    )
    .bind(auth.id)
    .fetch_all(&state.pool)
    .await?;

    let mut map = Map::new();
    for r in &rows {
        map.insert(r.roadmap_id.clone(), json!(r.ts));
    }
    Ok(Json(Value::Object(map)))
}
