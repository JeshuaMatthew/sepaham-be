# Sepaham Backend

REST API for **Sepaham** — the community & career platform for IT students.
Built with **Axum** (Rust) + **SQLx** + **PostgreSQL**.

This first pass ships the **foundation**: the full database schema for every
frontend feature, SQLx migrations (schema + seeded reference data), the Axum
app skeleton (config, connection pool, error handling, CORS), and a working
**auth** flow (register / login / JWT / me). Feature endpoints (roadmaps, chat,
collab, career, faculty…) build on top of this in later passes.

## Stack

| Concern        | Choice                                             |
| -------------- | -------------------------------------------------- |
| HTTP framework | [Axum](https://github.com/tokio-rs/axum) 0.8       |
| Async runtime  | Tokio                                              |
| Database       | PostgreSQL 16                                       |
| DB access      | SQLx 0.8 (pure-Rust, async, no libpq)              |
| Migrations     | SQLx embedded migrator (`migrations/*.up.sql`)     |
| Auth           | JWT (`jsonwebtoken`) + Argon2 password hashing     |

SQLx uses **runtime** queries (not the compile-time `query!` macros), so the
project builds without a live database connection.

## Prerequisites

- Rust (stable, 2021 edition) — `cargo`, `rustc`
- Docker (for local Postgres) — or an existing Postgres 16 instance

The `diesel` CLI, `libpq`, and a local Postgres install are **not** required.

## Quick start

```bash
cd backend

# 1. Start Postgres (uses docker-compose.yml)
docker compose up -d

# 2. Configure environment
cp .env.example .env        # adjust if needed

# 3. Run — migrations apply automatically on startup
cargo run
```

The API listens on `http://localhost:8080` by default. Migrations in
`migrations/` run automatically each time the app starts (already-applied ones
are skipped).

### Health check

```bash
curl http://localhost:8080/health
# {"status":"ok"}
```

## Configuration

All configuration comes from environment variables (loaded from `.env` in
development). See [`.env.example`](.env.example).

| Variable                | Default                                             | Purpose                              |
| ----------------------- | --------------------------------------------------- | ------------------------------------ |
| `DATABASE_URL`          | —  (**required**)                                   | Postgres connection string           |
| `JWT_SECRET`            | `dev-secret-change-me`                              | Secret used to sign JWTs             |
| `JWT_EXPIRY_HOURS`      | `72`                                                | Access-token lifetime                |
| `BIND_ADDR`             | `0.0.0.0:8080`                                       | Listen address                       |
| `CORS_ALLOWED_ORIGINS`  | `http://localhost:5173,http://localhost:5174`       | Comma-separated allowed origins      |
| `RUST_LOG`              | `info`                                               | Log filter (tracing EnvFilter)       |

## Migrations

Migrations are plain `.sql` files under `migrations/`, run by the embedded SQLx
migrator (`sqlx::migrate!`) at startup — no CLI needed.

| File                              | Contents                                             |
| --------------------------------- | ---------------------------------------------------- |
| `0001_init.up.sql`                | Full schema: enums + all tables for every domain     |
| `0002_seed_reference_data.up.sql` | Seed roles, questions, badges, servers, roadmaps…    |

Each has a matching `.down.sql` for reversibility. To add a migration, create
`NNNN_name.up.sql` / `NNNN_name.down.sql` with the next number.

If you install the SQLx CLI (`cargo install sqlx-cli --no-default-features
--features rustls,postgres`) you can also run `sqlx migrate run` / `revert`
manually, but it is optional.

### Seeding roadmap skill-trees

The migrations seed the roadmap *catalog* but not the full node/edge trees (that
content is large and authored). To load the demo trees from the frontend mock
JSON, run once with the server up:

```bash
node scripts/seed_roadmaps.mjs           # defaults to http://localhost:8080/api
```

It registers (or logs in) a faculty account and `PUT`s each tree via
`PUT /api/roadmaps/{id}`, deriving edges from legacy `prereqs` where a mock has
no explicit `edges`.

## API

Base path for feature routes: `/api`.

### Auth (`/api/auth`) — implemented

| Method | Path                 | Auth   | Body / notes                                         |
| ------ | -------------------- | ------ | ---------------------------------------------------- |
| POST   | `/api/auth/register` | public | `{ email, password, name, role? }` → `{ token, user }` (201) |
| POST   | `/api/auth/login`    | public | `{ email, password }` → `{ token, user }`            |
| GET    | `/api/auth/me`       | bearer | → current `user`                                     |

`role` is `"student"` (default) or `"faculty"`. Authenticated requests send
`Authorization: Bearer <token>`. The `user` object is
`{ id, email, name, role, isNewUser }`.

Example:

```bash
# Register
curl -X POST http://localhost:8080/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"rangga@student.id","password":"secret123","name":"Rangga"}'

# Login
curl -X POST http://localhost:8080/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"rangga@student.id","password":"secret123"}'

# Me
curl http://localhost:8080/api/auth/me -H "Authorization: Bearer <token>"
```

### Content / catalog (`/api`) — implemented, public

These back the frontend's read-only content services and return the same JSON
shapes the mock files did.

| Method | Path                          | Returns                                             |
| ------ | ----------------------------- | --------------------------------------------------- |
| GET    | `/api/roles`                  | `{ roles: Role[] }`                                 |
| GET    | `/api/onboarding/questions`   | `{ questions: LikertQuestion[] }`                   |
| GET    | `/api/badges`                 | `{ badges: Badge[] }` (`earned:false` w/o a user)   |
| GET    | `/api/roadmaps`               | `{ roadmaps: RoadmapSummary[] }` (`totalNodes` computed) |
| GET    | `/api/roadmaps/{id}`          | `Roadmap` (nodes + edges + style; tolerant of unknown id) |
| GET    | `/api/internships/contacts`   | `{ contacts: InternshipContact[] }`                 |
| GET    | `/api/ai/feed`                | `{ quotes, nudge, internships }`                    |
| GET    | `/api/music/lofi`             | `{ tracks: LofiTrack[] }`                           |
| GET    | `/api/community/servers`      | `{ servers: Server[] }` (excludes banned)           |
| GET    | `/api/community/channels`     | `{ channels: Channel[] }`                           |

### Roadmaps (`/api`) — implemented

| Method | Path                                                | Auth    | Notes                                                  |
| ------ | --------------------------------------------------- | ------- | ------------------------------------------------------ |
| GET    | `/api/roadmaps`                                     | public  | `{ roadmaps: RoadmapSummary[] }` (`totalNodes` computed) |
| GET    | `/api/roadmaps/{id}`                                | public  | `Roadmap` (nodes + edges + style; tolerant of unknown id) |
| PUT    | `/api/roadmaps/{id}`                                | faculty | Upsert meta + **replace** nodes/edges (the editor's save) |
| GET    | `/api/roadmaps/{id}/submissions`                    | bearer  | `{ [nodeKey]: SubmissionState }` for the current user  |
| PUT    | `/api/roadmaps/{id}/nodes/{nodeKey}/submission`     | bearer  | `{ done, fileName?, text?, score?, quizAnswers? }` (upsert) |
| POST   | `/api/roadmaps/{id}/activity`                       | bearer  | Mark roadmap recently opened                           |
| GET    | `/api/roadmap-activity`                             | bearer  | `{ [roadmapId]: epochMillis }`                         |

### Onboarding questionnaire (`/api`) — implemented

| Method | Path                          | Auth    | Notes                                       |
| ------ | ----------------------------- | ------- | ------------------------------------------- |
| GET    | `/api/onboarding/questions`   | public  | `{ questions: LikertQuestion[] }`           |
| PUT    | `/api/onboarding/questions`   | faculty | `{ questions: [...] }` — replace the set     |

### Profile & preferences (`/api`) — implemented, bearer

| Method | Path                | Body / notes                                              |
| ------ | ------------------- | --------------------------------------------------------- |
| GET    | `/api/profile`      | → `Profile`                                               |
| PUT    | `/api/profile`      | partial `Profile` fields → updated `Profile` (COALESCE)   |
| GET    | `/api/preferences`  | → onboarding preference, or `null` if not onboarded       |
| PUT    | `/api/preferences`  | `{ roleId, roleTitle, roleEmoji, roleScores }` (upsert)   |

### Collab — "Cari Tim" (`/api/collab`) — implemented

| Method | Path                                               | Auth   | Notes                                                        |
| ------ | -------------------------------------------------- | ------ | ----------------------------------------------------------- |
| GET    | `/api/collab/requests`                             | public | `{ requests: CollabRequest[] }` (open, not closed)          |
| POST   | `/api/collab/requests`                             | bearer | Create; body may include `newCommunityName` **or** `communityId`. Creates a new team community (+ `general`/`progress` channels, creator as member) when no `communityId`. → created `CollabRequest` (201) |
| GET    | `/api/collab/my-teams`                             | bearer | `{ teams: [{ request, applicants, communityServerId }] }`   |
| POST   | `/api/collab/requests/{id}/apply`                  | bearer | `{ message? }` → applicant (201). Guards own-request (400) & duplicates (409) |
| PATCH  | `/api/collab/requests/{id}/applicants/{aid}`       | bearer | Owner only. `{ status: "accepted" \| "rejected" }`. Accept adds the applicant to the community + bumps `membersCurrent` (marks `full` when reached) |

### GitHub dev-card (`/api/github`) — implemented, bearer

| Method | Path                    | Notes                                                        |
| ------ | ----------------------- | ----------------------------------------------------------- |
| POST   | `/api/github/connect`   | `{ username? }` → marks profile connected + imports a demo snapshot → `GithubStats` |
| GET    | `/api/github`           | → `GithubStats`, or 404 if not connected                    |

`GET /api/profile` now also returns `githubConnected` / `githubUsername`.

### Community membership & invites (`/api/community`) — implemented

| Method | Path                                          | Auth   | Notes                                                    |
| ------ | --------------------------------------------- | ------ | -------------------------------------------------------- |
| GET    | `/api/community/mine`                          | bearer | `{ communities: [{ server, channels }] }` the user is in |
| POST   | `/api/community/servers/{id}/join`             | bearer | Join by server id (invite link) → `{ server, channels }` |
| POST   | `/api/community/servers/{id}/invites`          | bearer | Members only → `{ token, serverId }` (201)               |
| POST   | `/api/community/invites/{token}/accept`        | bearer | Join via invite token → `{ server, channels }`           |

### Community chat (`/api`) — implemented

| Method | Path                              | Auth   | Notes                                                     |
| ------ | --------------------------------- | ------ | -------------------------------------------------------- |
| GET    | `/api/channels/{id}/messages`     | public | `ChatMessage[]` (top-level, each with nested `replies`)  |
| POST   | `/api/channels/{id}/messages`     | bearer | Send `{ text?, code?, attachment?, anonymous?, parentId? }` (a `parentId` makes it a thread reply) |
| GET    | `/api/dms`                        | bearer | `{ dms: DirectConversation[] }` for the current user     |
| POST   | `/api/dms`                        | bearer | `{ userId }` → open/create a DM, returns the conversation |
| POST   | `/api/dms/{dmId}/messages`        | bearer | Send a DM message (participant only)                     |

Migration `0004_seed_messages` seeds a few `#general` / `#frontend` messages
(incl. a code snippet, an attachment, and a threaded reply).

### Planned (schema ready, endpoints in later passes)

Per-user badges & GitHub dev-card · roadmap student submissions & activity ·
community messages/DMs · CV upload · career readiness · faculty dashboard &
moderation · faculty content editing (roadmap trees, questions).

## Frontend integration

The React frontend (`../frontend`) talks to this API through a shared axios
instance. To point it here, set in `frontend/.env`:

```
VITE_API_URL=http://localhost:8080/api
```

The instance attaches `Authorization: Bearer <jwt>` (stored in `localStorage`
after login/register) and CORS is configured for the Vite dev origins
(`5173`/`5174`). Wired so far: **auth** (register/login), **roles**,
**profile**, **badges**, **internship contacts**, **AI feed**, **lofi**,
**onboarding questions**, **roadmap catalog + trees**. Content services read
any local faculty override first, then fall back to the API.

**Progress sync (write-through):** onboarding **preference**, roadmap
**submissions**, and **activity** keep `localStorage` as the synchronous read
cache but push writes to the backend (`PUT /preferences`,
`PUT /roadmaps/{id}/nodes/{nodeKey}/submission`, `POST /roadmaps/{id}/activity`)
and hydrate from it — preference on login, submissions when a roadmap opens — so
progress survives across devices.

**Collab & community** are also wired: the "Cari Tim" list/create/my-teams and
applicant accept-reject hit `/api/collab/*`; team communities and the invite
`?join=` flow hit `/api/community/*` (the chat rail merges the user's
`/community/mine` team communities with the campus servers). Migration
`0003_seed_collab_requests` seeds a few demo requests so the list isn't empty.

**GitHub UI** (connect button + dev-card) and **faculty editing** (onboarding
questions, roadmap trees & catalog meta) are wired too — the faculty save
functions write their local override *and* push to the backend (`PUT
/onboarding/questions`, `PUT /roadmaps/{id}`).

**Community chat** is wired: servers/channels come from `/api/community/*`,
channel messages + threaded replies from `/api/channels/{id}/messages`, and DMs
from `/api/dms`. Ad-hoc "DM the author" panes opened from Cari Tim stay local
(the partner isn't necessarily a real user yet).

The whole frontend now talks to the API — the `public/mocks/*.json` files have
been removed. The few pieces without a backend endpoint (SSO provider list,
GitHub dev-card fallback, faculty student-dashboard demo) are inlined as small
constants in their services.

## Images

Stored images are re-encoded to **WebP** on the server and saved under
`uploads/`, served statically at `/uploads/<uuid>.webp` (loaded cross-origin as
`<img src>`, so no CORS needed). URLs are absolute using `PUBLIC_BASE_URL`.

- **On store** — collab-request images and roadmap-node images sent as `data:`
  URLs are decoded (`image` crate, pure Rust) and written as WebP; values that
  are already URLs pass through unchanged.
- **On delete** — `DELETE /api/collab/requests/{id}` (owner only) removes the
  request and its image files.
- **On replace** — saving a roadmap tree (`PUT /api/roadmaps/{id}`) deletes the
  files of node images that are no longer referenced.

The `uploads/` directory is git-ignored and recreated on startup.

## Database schema

The schema in `0001_init.up.sql` maps directly to the frontend's domains
(mirrors `frontend/src/types/*` and the localStorage stores that need to become
server-persisted):

- **Auth / profile** — `users`, `profiles`, `badges`, `user_badges`,
  `github_stats`, `github_repos`
- **Roles / onboarding** — `roles`, `hobbies`, `onboarding_questions`,
  `user_preferences`
- **Roadmaps** — `roadmaps`, `roadmap_nodes`, `roadmap_edges`, `submissions`,
  `roadmap_activity`
- **Community / chat** — `servers`, `channels`, `server_members`,
  `community_invites`, `direct_conversations`, `messages`
- **Collab ("Cari Tim")** — `collab_requests`, `collab_request_images`,
  `collab_applicants`
- **Reference / AI** — `internship_contacts`, `dev_quotes`, `ai_internships`,
  `lofi_tracks`

## Project layout

```
backend/
├─ Cargo.toml
├─ docker-compose.yml        # local Postgres
├─ .env.example
├─ migrations/               # SQLx .up.sql / .down.sql
└─ src/
   ├─ main.rs                # startup: config, pool, migrate, serve
   ├─ config.rs              # env-based configuration
   ├─ db.rs                  # pool + migration runner
   ├─ error.rs               # AppError → HTTP response
   ├─ state.rs               # shared AppState (pool + config)
   ├─ router.rs              # route table + CORS + tracing
   ├─ catalog.rs             # public content endpoints (roles, roadmaps, …)
   ├─ profile.rs             # profile + preferences (bearer)
   ├─ collab.rs              # Cari Tim: requests / applicants / my-teams
   ├─ community.rs           # membership + invite links
   ├─ github.rs              # dev-card: connect + stats
   ├─ chat.rs                # channel messages (threads) + DMs
   ├─ images.rs              # data-URL → WebP file, static serving, cleanup
   └─ auth/                  # register / login / me
      ├─ mod.rs              # /api/auth router
      ├─ handlers.rs
      ├─ models.rs           # User, DTOs, UserRole enum
      ├─ password.rs         # Argon2 hash/verify
      ├─ jwt.rs              # sign/verify JWT
      └─ extractor.rs        # AuthUser (Bearer) extractor
```
