-- Seed a few demo "Cari Tim" requests so the collab list isn't empty. These are
-- authorless (author_id NULL, denormalized author info) — they represent other
-- students' posts you can browse and apply to. Mirrors the frontend mock.

INSERT INTO collab_requests
    (id, author_id, author_name, author_avatar, author_role, title, description,
     needed_roles, tech_stack, tags, repo_url, community_id, members_current,
     members_needed, status, created_at)
VALUES
('a0000000-0000-4000-8000-0000000000c1', NULL, 'Kevin Wijaya', 'https://i.pravatar.cc/64?img=32', 'Frontend',
 'Aplikasi Absensi Kelas pakai QR',
 'Bikin app absensi berbasis QR buat tugas besar Rekayasa Perangkat Lunak. Butuh yang jago backend & mobile, deadline 6 minggu.',
 ARRAY['Backend','Mobile'], ARRAY['Go','Flutter'], ARRAY['Tugas Besar'],
 'https://github.com/kevinw/absensi-qr', NULL, 2, 4, 'open', now() - interval '30 minutes'),

('a0000000-0000-4000-8000-0000000000c2', NULL, 'Nabila Zahra', 'https://i.pravatar.cc/64?img=31', 'Product',
 'Startup Marketplace Jasa Mahasiswa',
 'Serius mau bangun startup marketplace jasa antar mahasiswa (join tim, split equity). Cari co-founder teknis & desainer yang komit jangka panjang.',
 ARRAY['Fullstack','UI/UX'], ARRAY['Next.js','PostgreSQL'], ARRAY['Startup'],
 NULL, NULL, 1, 3, 'open', now() - interval '120 minutes'),

('a0000000-0000-4000-8000-0000000000c3', NULL, 'Bagas Prasetyo', 'https://i.pravatar.cc/64?img=68', 'Backend',
 'Game Edukasi buat Lomba Hackathon',
 'Ikut hackathon bulan depan, tema teknologi pendidikan. Bikin game edukasi anak SD. Butuh 1 game dev & 1 artist.',
 ARRAY['Game Dev','Artist'], ARRAY['Unity','C#'], ARRAY['Hackathon'],
 NULL, NULL, 2, 4, 'open', now() - interval '240 minutes'),

('a0000000-0000-4000-8000-0000000000c4', NULL, 'Dinda Ayu', 'https://i.pravatar.cc/64?img=47', 'UI/UX',
 'Web Portofolio Komunitas Open Source',
 'Bikin website showcase project open-source anak kampus. Santai, buat belajar bareng & nambah portofolio.',
 ARRAY['Frontend','Backend'], ARRAY['React','Node.js'], ARRAY['Open Source','Santai'],
 'https://github.com/dindaa/oss-showcase', NULL, 3, 3, 'full', now() - interval '600 minutes'),

('a0000000-0000-4000-8000-0000000000c5', NULL, 'Salsabila', 'https://i.pravatar.cc/64?img=44', 'Data Scientist',
 'Aplikasi Deteksi Penyakit Tanaman (ML)',
 'Project ML klasifikasi penyakit daun pakai CNN, buat skripsi + submit ke jurnal. Butuh partner yang ngerti data & deployment.',
 ARRAY['Data/ML','Backend'], ARRAY['Python','PyTorch'], ARRAY['Skripsi','Riset'],
 'https://github.com/salsa/leaf-disease-cnn', NULL, 1, 2, 'open', now() - interval '45 minutes');

-- A few applicants so the "interested" counts aren't all zero.
INSERT INTO collab_applicants (request_id, user_id, name, avatar, role, message, status, created_at)
VALUES
('a0000000-0000-4000-8000-0000000000c1', NULL, 'Rina Melati', 'https://i.pravatar.cc/64?img=20', 'Backend', 'Tertarik bantu backend-nya!', 'pending', now() - interval '20 minutes'),
('a0000000-0000-4000-8000-0000000000c1', NULL, 'Yoga Pratama', 'https://i.pravatar.cc/64?img=52', 'Mobile', 'Bisa handle Flutter.', 'pending', now() - interval '15 minutes'),
('a0000000-0000-4000-8000-0000000000c1', NULL, 'Aditya Nugroho', 'https://i.pravatar.cc/64?img=11', 'Backend', 'Go developer di sini.', 'pending', now() - interval '10 minutes'),
('a0000000-0000-4000-8000-0000000000c2', NULL, 'Putri Ananda', 'https://i.pravatar.cc/64?img=25', 'UI/UX', 'Desainer, mau ikut!', 'pending', now() - interval '90 minutes'),
('a0000000-0000-4000-8000-0000000000c2', NULL, 'Reza Fauzan', 'https://i.pravatar.cc/64?img=33', 'Fullstack', 'Komit jangka panjang.', 'pending', now() - interval '60 minutes'),
('a0000000-0000-4000-8000-0000000000c3', NULL, 'Citra Dewi', 'https://i.pravatar.cc/64?img=48', 'Artist', 'Bisa bikin aset game.', 'pending', now() - interval '120 minutes'),
('a0000000-0000-4000-8000-0000000000c5', NULL, 'Melati Sari', 'https://i.pravatar.cc/64?img=25', 'Data/ML', 'Ngerti CNN & deployment.', 'pending', now() - interval '30 minutes');
