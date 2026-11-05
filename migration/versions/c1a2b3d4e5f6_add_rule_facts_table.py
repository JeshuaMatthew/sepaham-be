"""add_rule_facts_table_and_refactor_rules_roles

Revision ID: c1a2b3d4e5f6
Revises: b8c9d0e1f2a3
Create Date: 2026-11-02 17:30:00.000000

Pembaruan skema sistem pakar:
1. Menambahkan tabel relasi `rule_facts` antara rules dan facts:
   - id: UUID (Primary Key)
   - rule_id: UUID (Foreign Key ke rules.id)
   - fact_id: VARCHAR(50) (Foreign Key ke facts.id)
   - expected_value: BOOLEAN (True/False)
2. Menghubungkan `roles` ke `pillars` via kolom `roles.pillar_id`.
3. Menambahkan kolom `priority` ke `rules` untuk resolusi konflik dan menghapus `min_confidence_score`.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c1a2b3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Tabel rule_facts
    bind.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS rule_facts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                rule_id UUID NOT NULL REFERENCES rules(id) ON DELETE CASCADE,
                fact_id VARCHAR(50) NOT NULL REFERENCES facts(id) ON DELETE CASCADE,
                expected_value BOOLEAN NOT NULL DEFAULT true
            )
            """
        )
    )
    bind.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_rule_facts_rule_id "
            "ON rule_facts (rule_id)"
        )
    )
    bind.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_rule_facts_fact_id "
            "ON rule_facts (fact_id)"
        )
    )

    # 2. Tambah kolom priority ke rules jika belum ada, dan drop min_confidence_score
    bind.execute(
        sa.text(
            "ALTER TABLE rules ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 1"
        )
    )
    bind.execute(
        sa.text(
            "ALTER TABLE rules DROP COLUMN IF EXISTS min_confidence_score"
        )
    )

    # 3. Hubungkan roles ke pillars (pillar_id)
    bind.execute(
        sa.text(
            "ALTER TABLE roles ADD COLUMN IF NOT EXISTS pillar_id VARCHAR(50) REFERENCES pillars(id) ON DELETE SET NULL"
        )
    )
    bind.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_roles_pillar_id ON roles (pillar_id)"
        )
    )

    # Petakan role yang ada ke pilar masing-masing
    bind.execute(
        sa.text(
            "UPDATE roles SET pillar_id = 'software_dev' WHERE id IN ('frontend-engineer', 'backend-engineer', 'mobile-developer', 'fullstack-engineer') AND pillar_id IS NULL"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE roles SET pillar_id = 'data_ai' WHERE id IN ('data-analyst', 'ml-engineer', 'data-engineer') AND pillar_id IS NULL"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE roles SET pillar_id = 'design_ux' WHERE id IN ('ui-ux-designer', 'product-designer', 'ux-researcher') AND pillar_id IS NULL"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE roles SET pillar_id = 'infra_security' WHERE id IN ('security-engineer', 'cloud-architect') AND pillar_id IS NULL"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE roles SET pillar_id = 'tech_management' WHERE id IN ('product-manager', 'scrum-master', 'tech-lead') AND pillar_id IS NULL"
        )
    )

    # 4. Sinkronisasi awal dari rules.conditions jika data rules dan facts sudah ada
    bind.execute(
        sa.text(
            """
            INSERT INTO rule_facts (rule_id, fact_id, expected_value)
            SELECT r.id, c.key, (c.value::text)::boolean
            FROM rules r,
            LATERAL jsonb_each(r.conditions::jsonb) AS c(key, value)
            WHERE EXISTS (SELECT 1 FROM facts f WHERE f.id = c.key)
              AND NOT EXISTS (
                  SELECT 1 FROM rule_facts rf
                  WHERE rf.rule_id = r.id AND rf.fact_id = c.key
              )
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DROP TABLE IF EXISTS rule_facts CASCADE"))
    bind.execute(sa.text("ALTER TABLE roles DROP COLUMN IF EXISTS pillar_id"))
    bind.execute(sa.text("ALTER TABLE rules DROP COLUMN IF EXISTS priority"))
    bind.execute(sa.text("ALTER TABLE rules ADD COLUMN IF NOT EXISTS min_confidence_score DOUBLE PRECISION DEFAULT 0.7"))


