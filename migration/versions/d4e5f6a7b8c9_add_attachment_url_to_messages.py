"""add_attachment_url_to_messages

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-29 11:00:00.000000

Kolom `messages.attachment_url` menyimpan URL berkas lampiran chat yang sudah
diunggah lewat POST /api/chat/attachments.

Sebelumnya lampiran chat hanya berupa klaim metadata (nama/jenis/ukuran) tanpa
berkas yang bisa dibuka — frontend mengirim konstanta `screenshot.png` 128 KB.
Sekarang pesan baru wajib menyertakan URL hasil unggah supaya lampiran yang
tampil benar-benar bisa dibuka penerima.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("attachment_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "attachment_url")
