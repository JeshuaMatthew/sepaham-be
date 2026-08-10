-- Seed a few campus-channel messages so channels aren't empty. Authorless
-- (author_id NULL, denormalized author info), including a code snippet, an
-- attachment, and a threaded reply.

INSERT INTO messages
    (id, channel_id, parent_id, author_id, author_name, author_avatar, body,
     code_language, code_content, attachment_name, attachment_kind, attachment_size,
     anonymous, created_at)
VALUES
-- #general
(gen_random_uuid(), 'general', NULL, NULL, 'Rangga Pratama', 'https://i.pravatar.cc/64?img=13',
 'Halo semua! Ada yang lagi ngerjain tugas Sistem Basis Data?', NULL, NULL, NULL, NULL, NULL, false, now() - interval '55 minutes'),
(gen_random_uuid(), 'general', NULL, NULL, 'Nadia Putri', 'https://i.pravatar.cc/64?img=45',
 'Aku baru mulai ERD-nya, kamu udah sampai mana?', NULL, NULL, NULL, NULL, NULL, false, now() - interval '52 minutes'),
(gen_random_uuid(), 'general', NULL, NULL, 'Budi Santoso', 'https://i.pravatar.cc/64?img=12',
 'Nih aku share draft skemanya ya.', NULL, NULL, 'skema-db.pdf', 'file', '820 KB', false, now() - interval '48 minutes'),

-- #frontend (parent + threaded reply)
('b0000000-0000-4000-8000-0000000000f1', 'frontend', NULL, NULL, 'Rangga Pratama', 'https://i.pravatar.cc/64?img=13',
 'Ini cara convert design token ke CSS variables:', 'css',
 ':root {\n  --color-primary: #e5e5e5;\n  --color-ink: #282520;\n}', NULL, NULL, NULL, false, now() - interval '40 minutes'),
(gen_random_uuid(), 'frontend', 'b0000000-0000-4000-8000-0000000000f1', NULL, 'Nadia Putri', 'https://i.pravatar.cc/64?img=45',
 'Mantap, makasih! Langsung kupakai.', NULL, NULL, NULL, NULL, NULL, false, now() - interval '38 minutes');
