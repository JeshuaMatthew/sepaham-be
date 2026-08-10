-- Seed reference/lookup content so the API returns real data out of the box.
-- Mirrors the frontend mock JSON (public/mocks/*). User-authored content
-- (roadmap trees, messages, collab requests) is created at runtime, not seeded.

-- ---------------------------------------------------------------------------
-- Roles
-- ---------------------------------------------------------------------------
INSERT INTO roles (id, title, tagline, description, accent, match_tags, tech_stack, sort_order) VALUES
('frontend-engineer', 'Frontend Engineer', 'Building interfaces that feel alive & smooth.',
 'You love making things you can see and touch right away. Focused on interactive UI, animation, and user experience.',
 '#e5e5e5', ARRAY['web-dev','ui-ux','open-source','gaming'], ARRAY['React','TypeScript','Tailwind'], 1),
('backend-engineer', 'Backend Engineer', 'The scalable engine behind the scenes.',
 'You enjoy thinking about data structures, APIs, and performance. Logic and efficiency are your playground.',
 '#e5e5e5', ARRAY['web-dev','competitive-programming','cloud-devops','open-source'], ARRAY['Rust','Go','PostgreSQL'], 2),
('mobile-developer', 'Mobile Developer', 'Apps in the hands of millions.',
 'You want your work in everyone''s pocket. Focused on responsive Android/iOS apps.',
 '#e5e5e5', ARRAY['mobile-dev','ui-ux','gaming'], ARRAY['Kotlin','Swift','Flutter'], 3),
('ml-engineer', 'ML / AI Engineer', 'Teaching machines to think.',
 'You''re curious about patterns and prediction. Building models that learn from data is your passion.',
 '#e5e5e5', ARRAY['machine-learning','data-analytics','competitive-programming'], ARRAY['Python','PyTorch','Pandas'], 4),
('data-analyst', 'Data Analyst', 'Turning numbers into decisions.',
 'You''re great at finding the story behind the data and telling it clearly.',
 '#e5e5e5', ARRAY['data-analytics','writing','machine-learning'], ARRAY['SQL','Python','Looker'], 5),
('devops-engineer', 'DevOps / Cloud Engineer', 'Automation, deploys, and 99.9% uptime.',
 'You love making systems run automatically and reliably, from CI/CD to cloud infrastructure.',
 '#e5e5e5', ARRAY['cloud-devops','open-source','cybersecurity'], ARRAY['Docker','Kubernetes','Terraform'], 6),
('security-engineer', 'Security Engineer', 'The gatekeeper of the digital world.',
 'You think like an attacker in order to defend. Focused on system and network security.',
 '#e5e5e5', ARRAY['cybersecurity','competitive-programming','open-source'], ARRAY['Linux','Python','Burp Suite'], 7),
('game-developer', 'Game Developer', 'Building worlds you can play.',
 'You want to combine logic, art, and story into a fun playing experience.',
 '#e5e5e5', ARRAY['game-dev','gaming','ui-ux','anime'], ARRAY['Unity','C#','Godot'], 8),
('ui-ux-designer', 'UI/UX Designer', 'Empathy translated into design.',
 'You care about how people feel using a product. Research, wireframes, and prototypes.',
 '#e5e5e5', ARRAY['ui-ux','photography','writing'], ARRAY['Figma','Framer','Miro'], 9),
('fullstack-engineer', 'Fullstack / Product Engineer', 'From idea to deploy, you can do it all.',
 'You love building whole features — frontend, backend, all the way to release. A product-minded generalist.',
 '#e5e5e5', ARRAY['web-dev','ui-ux','writing','open-source','cloud-devops'], ARRAY['Next.js','Node.js','PostgreSQL'], 10);

-- ---------------------------------------------------------------------------
-- Hobbies
-- ---------------------------------------------------------------------------
INSERT INTO hobbies (id, label, sort_order) VALUES
('competitive-programming', 'Competitive Programming', 1),
('web-dev', 'Web Development', 2),
('mobile-dev', 'Mobile Dev', 3),
('game-dev', 'Game Dev', 4),
('machine-learning', 'Machine Learning', 5),
('data-analytics', 'Data & Analytics', 6),
('cybersecurity', 'Cybersecurity', 7),
('cloud-devops', 'Cloud & DevOps', 8),
('open-source', 'Open Source', 9),
('ui-ux', 'UI/UX Design', 10),
('photography', 'Photography', 11),
('lofi-music', 'Lo-Fi & Music', 12),
('writing', 'Writing & Blogging', 13),
('anime', 'Anime & Manga', 14),
('gaming', 'Gaming', 15),
('coffee', 'Coffee Nerd', 16);

-- ---------------------------------------------------------------------------
-- Onboarding questionnaire (Likert)
-- ---------------------------------------------------------------------------
INSERT INTO onboarding_questions (id, text, role_id, sort_order) VALUES
('q1', 'I enjoy designing and polishing an app''s interface.', 'frontend-engineer', 1),
('q2', 'I like building things that are instantly visible & interactive on screen.', 'frontend-engineer', 2),
('q3', 'I''m interested in designing data structures, APIs, and behind-the-scenes logic.', 'backend-engineer', 3),
('q4', 'I enjoy thinking about system performance, security, and scalability.', 'backend-engineer', 4),
('q5', 'I''m curious about finding patterns in data and making predictions.', 'ml-engineer', 5),
('q6', 'I''m comfortable working with math, statistics, and model experiments.', 'ml-engineer', 6),
('q7', 'I want to build apps used right from a phone.', 'mobile-developer', 7),
('q8', 'I like optimizing the experience on mobile devices (Android/iOS).', 'mobile-developer', 8);

-- ---------------------------------------------------------------------------
-- Badge catalog
-- ---------------------------------------------------------------------------
INSERT INTO badges (id, name, description, tier, sort_order) VALUES
('first-commit', 'First Blood', 'Your first commit to a public repo.', 'common', 1),
('streak-7', 'Consistent', 'A 7-day streak.', 'common', 2),
('streak-30', 'On Fire', 'A 30-day streak.', 'rare', 3),
('polyglot', 'Polyglot', 'Coded in 5+ different languages.', 'rare', 4),
('contributor', 'Contributor', 'Merged a PR into an open-source project.', 'epic', 5),
('rising-star', 'Rising Star', 'One of your repos hit 100 stars.', 'epic', 6),
('night-owl', 'Night Owl', 'Committed at midnight 10 times.', 'common', 7),
('mentor', 'Mentor', 'Helped 10 people in a discussion channel.', 'legendary', 8);

-- ---------------------------------------------------------------------------
-- Community servers + channels (campus communities)
-- ---------------------------------------------------------------------------
INSERT INTO servers (id, name, initial, color) VALUES
('itb', 'ITB Computer Science', 'IT', '#e5e5e5'),
('ui',  'UI Computer Science',  'UI', '#e5e5e5'),
('ugm', 'UGM Computer Science', 'UG', '#e5e5e5');

INSERT INTO channels (id, server_id, name, topic, kind, sort_order) VALUES
('general',      'itb', 'general',  'General chat for campus folks', 'text', 1),
('ui-ux',        'itb', 'UI-UX',    'Design, prototyping & Figma discussion', 'text', 2),
('loker',        'itb', 'jobs',     'Internships, part-time & job openings', 'text', 3),
('frontend',     'itb', 'frontend', 'React, Vue, Svelte & friends', 'text', 4),
('tanya-anonim', 'itb', 'ask-anon', 'Ask anything, the asker''s identity stays hidden', 'anon', 5),
('ui-general',   'ui',  'general',  'General chat for UI Computer Science', 'text', 1),
('ui-riset',     'ui',  'research', 'Paper & research discussion', 'text', 2),
('ugm-general',  'ugm', 'general',  'General chat for UGM Computer Science', 'text', 1);

-- ---------------------------------------------------------------------------
-- Roadmap catalog (skill trees are added later via the faculty editor / import)
-- ---------------------------------------------------------------------------
INSERT INTO roadmaps (id, role_id, title, color, description, difficulty, match_tags, author) VALUES
('frontend', 'frontend-engineer', 'Frontend Engineer', '#e5e5e5',
 'Build interactive web interfaces — HTML, CSS, JS, React, all the way to deploy.',
 'Beginner', ARRAY['web-dev','ui-ux','open-source','gaming'], 'Dr. Andi Wijaya'),
('backend', 'backend-engineer', 'Backend Engineer', '#e5e5e5',
 'Build scalable APIs, databases, and the systems behind the scenes.',
 'Intermediate', ARRAY['web-dev','competitive-programming','cloud-devops','open-source'], 'Dr. Budi Santoso'),
('data', 'ml-engineer', 'Data & Machine Learning', '#e5e5e5',
 'Work with data and statistics, up to building models that learn on their own.',
 'Intermediate', ARRAY['machine-learning','data-analytics','competitive-programming'], 'Prof. Clara Halim'),
('mobile', 'mobile-developer', 'Mobile Developer', '#e5e5e5',
 'Build Android/iOS apps from scratch to publishing on the store.',
 'Beginner', ARRAY['mobile-dev','ui-ux','gaming'], 'Dr. Dewi Lestari');

-- ---------------------------------------------------------------------------
-- Internship contacts (unlocked by roadmap progress)
-- ---------------------------------------------------------------------------
INSERT INTO internship_contacts (id, company, position, role_id, location, type, pic, contact, note) VALUES
('fe1', 'Tokopedia', 'Frontend Engineer Intern', 'frontend-engineer', 'Jakarta', 'Hybrid', 'Rina — Talent Acquisition', 'internship@tokopedia.com', 'Sebut kamu dari Sepaham + lampirkan roadmap-mu.'),
('fe2', 'Gojek', 'Web Frontend Intern', 'frontend-engineer', 'Jakarta', 'On-site', 'Dimas — Engineering Manager', 'https://www.gojek.io/careers', 'Buka lowongan tiap kuartal.'),
('fe3', 'Ruangguru', 'Frontend Intern (React)', 'frontend-engineer', 'Remote', 'Remote', 'Tania — Recruiter', '+62 812-3456-7890', 'Chat WA, jam kerja 09.00–17.00.'),
('be1', 'Xendit', 'Backend Engineer Intern', 'backend-engineer', 'Jakarta', 'Hybrid', 'Kevin — Backend Lead', 'careers@xendit.co', 'Fokus Go & sistem pembayaran.'),
('be2', 'Traveloka', 'Software Engineer Intern (Backend)', 'backend-engineer', 'Jakarta', 'Hybrid', 'Sari — Recruiter', 'internship@traveloka.com', NULL),
('ml1', 'Kata.ai', 'ML Engineer Intern', 'ml-engineer', 'Jakarta', 'Remote', 'Adi — AI Team', 'hello@kata.ai', 'Bawa portofolio project ML.'),
('ml2', 'Bukalapak', 'Data Science Intern', 'ml-engineer', 'Jakarta', 'Hybrid', 'Maya — Data Team', 'https://careers.bukalapak.com', NULL),
('mo1', 'DANA', 'Android Engineer Intern', 'mobile-developer', 'Jakarta', 'On-site', 'Bagus — Mobile Lead', '081298765432', 'Kotlin & Jetpack Compose diutamakan. Chat via WA.'),
('mo2', 'Blibli', 'Mobile Engineer Intern', 'mobile-developer', 'Jakarta', 'Hybrid', 'Nina — Recruiter', 'internship@blibli.com', NULL);

-- ---------------------------------------------------------------------------
-- AI feed: dev quotes + suggested internships
-- ---------------------------------------------------------------------------
INSERT INTO dev_quotes (text, author) VALUES
('Talk is cheap. Show me the code.', 'Linus Torvalds'),
('First, solve the problem. Then, write the code.', 'John Johnson'),
('Code is like humor. When you have to explain it, it''s bad.', 'Cory House'),
('A programmer is a machine that turns coffee into code.', 'Anonymous'),
('Simplicity is the soul of efficiency.', 'Austin Freeman');

INSERT INTO ai_internships (id, company, role, location, type, match_percent, tags) VALUES
('i1', 'Tokopedia', 'Frontend Engineer Intern', 'Jakarta', 'Hybrid', 92, ARRAY['React','TypeScript','Tailwind']),
('i2', 'Ruangguru', 'Fullstack Engineer Intern', 'Remote', 'Remote', 85, ARRAY['Next.js','Node.js','PostgreSQL']),
('i3', 'Gojek', 'Mobile Engineer Intern', 'Jakarta', 'On-site', 74, ARRAY['Flutter','Kotlin','Firebase']),
('i4', 'Xendit', 'Backend Engineer Intern', 'Jakarta', 'Hybrid', 68, ARRAY['Go','Rust','Docker']);

-- ---------------------------------------------------------------------------
-- Lo-fi tracks (host playback during calls)
-- ---------------------------------------------------------------------------
INSERT INTO lofi_tracks (id, title, artist) VALUES
('t1', 'Late Night Commit', 'Lo-Fi Dev'),
('t2', 'Coffee & Compile', 'ChillCode'),
('t3', 'Debugging Rain', 'Ambient Stack'),
('t4', 'Deploy at Dawn', 'Synth Ops');
