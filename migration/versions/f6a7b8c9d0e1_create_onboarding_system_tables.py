"""create_onboarding_system_tables

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-29 12:30:00.000000

Membuat lima tabel subsistem onboarding: `pillars`, `facts`, `questions`,
`rules`, dan `user_onboarding_sessions`.

Tabel-tabel ini dideklarasikan di `onboarding/entity.py` dan SUDAH ADA di
database produksi (dibuat lewat SQL ad-hoc), tapi tidak ada satu pun migrasi
yang membuatnya — termasuk `9eca0fe13df8_add_onboarding_system_tables` yang
isi `upgrade()`-nya cuma `pass`. Akibatnya `alembic upgrade head` di database
kosong tidak pernah menghasilkan skema expert-system, dan seluruh alur
onboarding (analyze-essay → questions → evaluate) plus editor soal dosen mati
total di deploy baru.

Semua statement di sini `IF NOT EXISTS` supaya idempoten: aman dijalankan di
database yang tabelnya sudah ada, dan membuat tabel yang belum ada di
database kosong. Definisi kolom disamakan dengan skema yang sudah berjalan
(lihat `\\d pillars` dkk), bukan sekadar salinan entity, supaya tidak ada
drift antara migrasi dan kenyataan.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS pillars (
                id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT
            )
            """
        )
    )

    bind.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS facts (
                id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                category VARCHAR(50)
            )
            """
        )
    )

    bind.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS questions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                pillar_id VARCHAR(50) REFERENCES pillars(id) ON DELETE CASCADE,
                fact_id VARCHAR(50) REFERENCES facts(id) ON DELETE CASCADE,
                question_text TEXT NOT NULL,
                question_type VARCHAR(20) NOT NULL,
                options JSONB,
                sort_order INTEGER NOT NULL DEFAULT 0,
                weight DOUBLE PRECISION NOT NULL DEFAULT 1
            )
            """
        )
    )
    bind.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_questions_pillar_sort "
            "ON questions (pillar_id, sort_order)"
        )
    )

    bind.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS rules (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                role_id VARCHAR(50) REFERENCES roles(id) ON DELETE CASCADE,
                conditions JSONB NOT NULL,
                min_confidence_score DOUBLE PRECISION DEFAULT 0.7
            )
            """
        )
    )

    bind.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS user_onboarding_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                essay_text TEXT,
                selected_pillars JSONB,
                collected_facts JSONB,
                recommended_role_id VARCHAR(50) REFERENCES roles(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    # Urutan dibalik karena foreign key.
    bind.execute(sa.text("DROP TABLE IF EXISTS user_onboarding_sessions"))
    bind.execute(sa.text("DROP TABLE IF EXISTS rules"))
    bind.execute(sa.text("DROP TABLE IF EXISTS questions"))
    bind.execute(sa.text("DROP TABLE IF EXISTS facts"))
    bind.execute(sa.text("DROP TABLE IF EXISTS pillars"))
