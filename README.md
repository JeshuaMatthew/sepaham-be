# Sepaham Backend (Python / FastAPI)

Backend REST API & Realtime WebSocket server untuk platform Sepaham menggunakan FastAPI, SQLAlchemy (asyncio), PostgreSQL, dan LiveKit.

## Persyaratan
- Python >= 3.14 (atau Python 3.11+ / uv)
- Docker & Docker Compose

## Setup & Menjalankan

### 1. Jalankan Database & SFU LiveKit (Docker)
```bash
docker compose up -d
```
Service yang berjalan:
- PostgreSQL 16: port `5432` (`sepaham-db`)
- LiveKit SFU: port `7880` (HTTP/WS), `7881` (TCP), `7882` (UDP) (`sepaham-livekit`)

### 2. Konfigurasi Environment
Pastikan file `.env` sudah sesuai (lihat `.env.example`):
```env
DB_URL=postgresql+asyncpg://sepaham:sepaham@localhost:5432/sepaham
JWT_SECRET=dev-secret-change-me-please-use-a-long-random-string
JWT_EXPIRY_HOURS=72
BIND_ADDR=0.0.0.0:8000
PUBLIC_BASE_URL=http://localhost:8000
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:5176
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
```

### 3. Migrasi & Seed Database (Alembic)
Jalankan migrasi database. Migrasi akan secara otomatis membuat tabel dan mengisi seluruh initial reference & dummy data (roles, hobbies, badges, servers/channels, roadmaps, nodes/edges, collab requests, messages, dan akun demo faculty/students):
```bash
uv run alembic upgrade head
```

#### Akun Demo Bawaan:
- **Faculty / Dosen**: `seed-faculty@sepaham.local` (Password: `seedfaculty123`)
- **Mahasiswa**:
  - `siti@sepaham.local` (Password: `password123`) — Frontend
  - `budi@sepaham.local` (Password: `password123`) — Backend
  - `nadia@sepaham.local` (Password: `password123`) — UI/UX
  - `rian@sepaham.local` (Password: `password123`) — Mobile
  - `salsa@sepaham.local` (Password: `password123`) — Data/ML
  - `kevin@sepaham.local` (Password: `password123`) — Fullstack

### 4. Jalankan Server FastAPI
```bash
uv run uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --reload
```
API akan berjalan di `http://localhost:8000/api` dan dokumentasi Swagger di `http://localhost:8000/docs`.
