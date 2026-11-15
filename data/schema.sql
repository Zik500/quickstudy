-- QuickStudy database schema for Supabase (PostgreSQL).
-- Run this whole file once in Supabase: Dashboard -> SQL Editor -> New query -> paste -> Run.
-- It is safe to run again: tables are only created if they do not exist yet.

-- A student, identified by the name typed in the sidebar
create table if not exists users (
    id          bigint generated always as identity primary key,
    name        text not null unique,
    exam_date   date,                                   -- for "Exam in N days" on Home
    created_at  timestamptz not null default now()
);

-- One uploaded PDF = one chapter in "My Notes"
create table if not exists library_files (
    id           bigint generated always as identity primary key,
    user_id      bigint not null references users (id) on delete cascade,
    file_name    text not null,                         -- e.g. "Chapter 1 - Testing Basics.pdf"
    file_hash    text,                                  -- md5 of the PDF, to spot the same file uploaded again
    pages        jsonb not null default '[]'::jsonb,    -- text of each page, ["page 1 text", "page 2 text", ...]
    text         text not null default '',              -- all pages joined
    text_source  text not null default 'pypdf',         -- "pypdf" or "Gemini Vision" (scanned PDFs)
    outline      jsonb,                                 -- [{"title": "...", "description": "..."}]
    created_at   timestamptz not null default now(),
    unique (user_id, file_name)
);

-- AI study notes, one per chapter and language
create table if not exists study_notes (
    id            bigint generated always as identity primary key,
    file_id       bigint not null references library_files (id) on delete cascade,
    language      text not null,                        -- "English" or "Bahasa Melayu"
    content       text not null,                        -- Markdown
    generated_by  text not null,                        -- e.g. "Groq (openai/gpt-oss-120b)"
    created_at    timestamptz not null default now(),
    unique (file_id, language)
);

-- One submitted quiz
create table if not exists quiz_attempts (
    id          bigint generated always as identity primary key,
    user_id     bigint not null references users (id) on delete cascade,
    chapters    jsonb not null default '[]'::jsonb,     -- ["Chapter 1 - Testing Basics", ...]
    settings    jsonb not null default '{}'::jsonb,     -- {"difficulty", "count", "source", "generated_by"}
    label       text not null default 'normal' check (label in ('normal', 'revision')),
    score       int  not null,
    total       int  not null,
    created_at  timestamptz not null default now()
);

-- Every question of a submitted quiz with the student's answer (used for Weak Topics and History)
create table if not exists answers (
    id              bigint generated always as identity primary key,
    attempt_id      bigint not null references quiz_attempts (id) on delete cascade,
    question        text not null,
    topic           text not null,                      -- short topic, e.g. "Defect Rejection Ratio"
    chapter         text not null default '',
    user_answer     text not null,
    correct_answer  text not null,
    is_correct      boolean not null,
    reported        boolean not null default false,     -- "⚑ Report question": not counted as a weak topic
    created_at      timestamptz not null default now()
);

-- The AI study plan for one day
create table if not exists study_plans (
    id          bigint generated always as identity primary key,
    user_id     bigint not null references users (id) on delete cascade,
    plan_date   date not null,
    tasks       jsonb not null default '[]'::jsonb,     -- [{"title", "reason", "action", "chapter"}]
    created_at  timestamptz not null default now(),
    unique (user_id, plan_date)
);

-- Faster lookups by user / attempt / file
create index if not exists library_files_user_idx on library_files (user_id);
create index if not exists study_notes_file_idx on study_notes (file_id);
create index if not exists quiz_attempts_user_idx on quiz_attempts (user_id);
create index if not exists answers_attempt_idx on answers (attempt_id);

-- Row Level Security is OFF.
-- student prototype, no auth - enable RLS in production
alter table users disable row level security;
alter table library_files disable row level security;
alter table study_notes disable row level security;
alter table quiz_attempts disable row level security;
alter table answers disable row level security;
alter table study_plans disable row level security;
