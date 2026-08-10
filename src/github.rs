//! GitHub dev-card. In the absence of a real OAuth integration yet, "connect"
//! marks the profile connected and imports a demo stats snapshot for the user;
//! `GET /api/github` returns it in the frontend's `GithubStats` shape.

use axum::extract::State;
use axum::routing::{get, post};
use axum::{Json, Router};
use serde::Deserialize;
use serde_json::{json, Value};
use uuid::Uuid;

use crate::auth::extractor::AuthUser;
use crate::error::{AppError, AppResult};
use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/github", get(get_stats))
        .route("/github/connect", post(connect))
}

#[derive(sqlx::FromRow)]
struct StatsRow {
    username: String,
    total_commits: i32,
    current_streak: i32,
    longest_streak: i32,
    public_repos: i32,
    top_languages: Value,
    weeks: Value,
}

#[derive(sqlx::FromRow)]
struct RepoRow {
    name: String,
    description: String,
    stars: i32,
    forks: i32,
    language: String,
    language_color: String,
    url: String,
}

async fn build_stats(state: &AppState, user_id: Uuid) -> AppResult<Option<Value>> {
    let stats = sqlx::query_as::<_, StatsRow>(
        "SELECT username, total_commits, current_streak, longest_streak, public_repos,
                top_languages, weeks
         FROM github_stats WHERE user_id = $1",
    )
    .bind(user_id)
    .fetch_optional(&state.pool)
    .await?;

    let Some(s) = stats else { return Ok(None) };

    let repos = sqlx::query_as::<_, RepoRow>(
        "SELECT name, description, stars, forks, language, language_color, url
         FROM github_repos WHERE user_id = $1 ORDER BY stars DESC",
    )
    .bind(user_id)
    .fetch_all(&state.pool)
    .await?;

    let top_repos: Vec<Value> = repos
        .iter()
        .enumerate()
        .map(|(i, r)| {
            json!({
                "id": format!("repo-{i}"),
                "name": r.name,
                "description": r.description,
                "stars": r.stars,
                "forks": r.forks,
                "language": r.language,
                "languageColor": r.language_color,
                "url": r.url,
            })
        })
        .collect();

    Ok(Some(json!({
        "username": s.username,
        "stats": {
            "totalCommits": s.total_commits,
            "currentStreak": s.current_streak,
            "longestStreak": s.longest_streak,
            "publicRepos": s.public_repos,
        },
        "topLanguages": s.top_languages,
        "weeks": s.weeks,
        "topRepos": top_repos,
    })))
}

/// GET /api/github — the current user's dev-card, or 404 if not connected.
async fn get_stats(State(state): State<AppState>, auth: AuthUser) -> AppResult<Json<Value>> {
    build_stats(&state, auth.id)
        .await?
        .map(Json)
        .ok_or_else(|| AppError::NotFound("github not connected".into()))
}

#[derive(Deserialize)]
struct ConnectInput {
    #[serde(default)]
    username: Option<String>,
}

/// POST /api/github/connect — mark connected + import a demo snapshot.
async fn connect(
    State(state): State<AppState>,
    auth: AuthUser,
    Json(input): Json<ConnectInput>,
) -> AppResult<Json<Value>> {
    let username = input
        .username
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .unwrap_or("yourhandle")
        .to_string();

    let top_languages = json!([
        { "name": "TypeScript", "percentage": 42, "color": "#3987e5" },
        { "name": "Rust",       "percentage": 24, "color": "#d95926" },
        { "name": "Go",         "percentage": 15, "color": "#199e70" },
        { "name": "Python",     "percentage": 12, "color": "#c98500" },
        { "name": "CSS",        "percentage": 7,  "color": "#d55181" }
    ]);

    // A compact 16-week contribution matrix (7 days each).
    let weeks = json!([
        [0,11,9,6,0,0,0],[0,9,4,0,0,11,2],[0,0,12,1,8,0,0],[0,3,0,7,9,10,0],
        [2,1,3,0,0,0,1],[0,9,10,8,0,0,0],[5,0,2,0,0,0,0],[0,5,4,5,0,5,1],
        [3,8,5,0,0,7,0],[4,1,7,1,0,8,0],[3,4,0,0,4,6,0],[0,5,0,12,8,5,0],
        [0,0,0,12,3,3,5],[6,2,0,4,0,0,1],[0,7,9,0,2,0,0],[1,0,3,5,8,0,0]
    ]);

    let mut tx = state.pool.begin().await?;

    sqlx::query(
        "UPDATE profiles SET github_connected = true, github_username = $2, updated_at = now()
         WHERE user_id = $1",
    )
    .bind(auth.id)
    .bind(&username)
    .execute(&mut *tx)
    .await?;

    sqlx::query(
        "INSERT INTO github_stats
            (user_id, username, total_commits, current_streak, longest_streak,
             public_repos, top_languages, weeks, updated_at)
         VALUES ($1, $2, 1245, 17, 63, 28, $3, $4, now())
         ON CONFLICT (user_id) DO UPDATE SET
            username = EXCLUDED.username, top_languages = EXCLUDED.top_languages,
            weeks = EXCLUDED.weeks, updated_at = now()",
    )
    .bind(auth.id)
    .bind(&username)
    .bind(&top_languages)
    .bind(&weeks)
    .execute(&mut *tx)
    .await?;

    sqlx::query("DELETE FROM github_repos WHERE user_id = $1")
        .bind(auth.id)
        .execute(&mut *tx)
        .await?;

    let demo_repos = [
        ("sepaham-fe", "Frontend for the Sepaham platform", 128, 18, "TypeScript", "#3987e5"),
        ("rust-axum-api", "Async REST API playground", 74, 9, "Rust", "#d95926"),
        ("dsa-notes", "Data structures & algorithms notes", 41, 5, "Python", "#c98500"),
    ];
    for (name, desc, stars, forks, lang, color) in demo_repos {
        sqlx::query(
            "INSERT INTO github_repos
                (user_id, name, description, stars, forks, language, language_color, url)
             VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
        )
        .bind(auth.id)
        .bind(name)
        .bind(desc)
        .bind(stars)
        .bind(forks)
        .bind(lang)
        .bind(color)
        .bind(format!("https://github.com/{username}/{name}"))
        .execute(&mut *tx)
        .await?;
    }

    tx.commit().await?;

    let stats = build_stats(&state, auth.id)
        .await?
        .ok_or_else(|| AppError::Internal("failed to build github stats".into()))?;
    Ok(Json(stats))
}
