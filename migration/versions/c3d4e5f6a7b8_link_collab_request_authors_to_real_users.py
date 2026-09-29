"""link_collab_request_authors_to_real_users

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-29 10:15:00.000000

Mengisi `collab_requests.author_id` yang sebelumnya `NULL`.

Semua lima request hasil seed cuma punya `author_name`, jadi `author_id`-nya
kosong. Akibatnya:

- `DELETE /api/collab/requests/{id}` membandingkan `c.author_id != user_id`,
  jadi tidak ada user yang bisa menghapus requestnya sendiri.
- Tombol "Gabung via DM" tidak bisa dibuka, karena frontend butuh user id
  sungguhan untuk membuat percakapan, dan tidak ada alur menebak user dari
  nama.

Migrations di bawah menautkan tiap request ke user seed yang namanya cocok
dengan `author_name`, jadi kolom `author_id` akhirnya konsisten dengan
`author_name` yang sudah tampil di UI. Request yang namanya tidak ada
tetap dibiarkan `NULL` — lebih jujur daripada menautkannya ke user yang salah.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE collab_requests AS c
               SET author_id = u.id
              FROM users AS u
             WHERE c.author_id IS NULL
               AND lower(c.author_name) = lower(u.name)
            """
        )
    )


def downgrade() -> None:
    # Mengembalikan `author_id` ke NULL. Nama di `author_name` tidak diubah,
    # jadi kondisinya sama seperti sebelum migrasi ini.
    op.get_bind().execute(
        sa.text("UPDATE collab_requests SET author_id = NULL WHERE author_id IS NOT NULL")
    )
