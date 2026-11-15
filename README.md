# QuickStudy

QuickStudy is a Streamlit app that helps students revise from their own lecture notes.
Upload your PDFs and the app will:

1. **Show a Study Dashboard (Home)**: a greeting with a message based on your progress (e.g. *"You have 3 weak
   topics. Let's fix them today."*), four stats (chapters, quizzes taken, average score, study streak),
   an **AI Study Plan for Today**, a **Continue where you left off** card (your last quiz, notes or question),
   and your **weakest topic** with a "Revise now" button.
   - **AI Study Plan**: set your exam date ("Exam in N days"), then click **Generate today's plan**. The AI
     suggests 3-4 tasks based on your weak topics, the chapters you have not quizzed yet and the days left.
     Each task is a checklist item with a button that opens the right section with the right chapter.
     The plan is saved for the day; **Regenerate** makes a new one.
   - Before you upload anything, Home shows a "Start by uploading your first chapter" card.
2. **Keep a notes library ("My Notes Library")**: PDFs are uploaded in one place only, the drag & drop card on
   the **Notes** page. Every PDF becomes a chapter in the library (no duplicates) and is listed in the sidebar
   under "My Notes" with a remove × button.
   - **Scanned PDFs**: if a PDF has very little text (less than 200 characters per page on average), its first
     10 pages are turned into images and read with **Gemini Vision**. The app then shows
     *"Text extracted by: Gemini Vision"*.
3. **Make a chapter outline**: when a PDF is added, the AI makes a short outline of it once (4-8 main sections,
   each with a one-line description). It is shown on the Notes page and used by Ask Notes.
4. **Ask Notes (tutor chat)**: its own page, laid out like a messaging app (your questions in purple bubbles on
   the right, answers on the left).
   - Choose the **"Chapters to ask about"** first. Answers come **only** from those chapters; if something is
     not in them, it replies *"This is not covered in your notes."*
   - **Clarifying questions**: for broad requests like "explain chapter 1", it asks *"Which part do you want me
     to explain?"* and shows the chapter's outline sections as clickable chips, plus *"Quick overview of
     everything"*.
   - Answers are written like a friendly tutor and end with *"Want me to explain another part or give you a
     quick question to test yourself?"* Quotes are hidden under **"📎 Sources from your notes"**.
   - Under each answer: **🔊 Listen · 📋 Copy · 🔄 Regenerate**, plus a **Clear chat** button.
5. **Write study notes**: choose a chapter and a language (English or Bahasa Melayu). Notes are saved per chapter
   and per language, so switching chapters is instant.
6. **Quiz you**: choose one or more chapters, the number of questions (5 or 10), the difficulty (Easy / Medium /
   Hard) and the source: *Study notes (fast)* or *Full PDF (detailed)* with optional page ranges.
   - **Correct answer keys**: the main Groq model writes the quiz with more careful reasoning ("medium") and
     strict rules (every question answerable from the notes, calculations worked out before choosing the
     answer). The app then checks every question **in code**: exactly 4 different options and the answer must
     be one of them. A bad question is rewritten once.
   - A progress box shows each step and how many seconds it took. The same chapters + settings reuse the saved
     quiz instantly; **New questions** makes a fresh one.
7. **Fast, clear results**: after **Submit** the score appears **immediately** (no AI call), with a short
   explanation for each question.
   - Each wrong answer shows a red **"✗ Your answer"** pill, a green **"✓ Correct answer"** pill and a 💡
     explanation. Correct answers are compact green cards, collapsed by default, so mistakes stand out.
   - **Explain more**: only when you click it, the AI writes a detailed explanation (why your answer is wrong,
     plus a quote from your notes in a collapsed "From your notes" box). Explanations never "think aloud"; if the
     AI believes the answer key is wrong it says *"This question may contain an error."*
   - **🔊 Listen**: the AI Audio Tutor explains the mistake out loud.
   - **⚑ Report question**: marks a question as wrong in your history, and it no longer counts as a weak topic.
8. **AI Audio Tutor**: a short spoken lesson about a chapter's study notes (key concepts, an everyday example and
   a question to think about), in English or Bahasa Melayu, with the script shown so you can read along.
9. **Track and revise weak topics**: mistakes per topic in a bar chart. Short topic names are shown as pills,
   with the chapter name as a small grey label. Revision quizzes are one click away after a quiz, on the
   Weak Topics page ("Revise Weak Topics" and "Practice" per topic) and on Home ("Revise now").
10. **Keep a quiz history**: every quiz from the session with its chapters, difficulty, score and reported
    questions.

## AI tools used and why

| Tool | Model | Role in the app | Why |
|------|-------|-----------------|-----|
| **Groq (main)** | `openai/gpt-oss-120b` | Primary AI: chapter outlines, study notes, quizzes and revision quizzes, AI Study Plan, detailed "Explain more" explanations | Very fast and has **higher free limits** |
| **Groq (fast)** | `openai/gpt-oss-20b` | Ask Notes chat and Audio Tutor scripts | Even faster replies for chat-style tasks |
| **Google Gemini** | `gemini-3.8-flash` | **Reliability backup** for every Groq task, and **Gemini Vision** for reading scanned PDFs | Can read images; keeps the app working when Groq is busy |
| **gTTS** | Google Text-to-Speech | Speaks Audio Tutor lessons and chat answers (English / Bahasa Melayu) | Free and simple **speech** |
| **sumy** | TextRank (runs locally) | Offline summary if no AI is available | **Offline fallback**: works with no API key |
| **Supabase** | PostgreSQL database | Saves each student's data (see "Database" below) | Free hosted database with a simple Python SDK |

### How the AI calls stay fast and reliable

- **Groq first, Gemini as backup** (`services/ai_router.py`): if Groq fails (429 rate limit, 5xx error, a
  timeout of about 20 seconds, or a reply that is not valid JSON), Gemini does the same task with the same
  prompt and JSON format. A small grey label shows *"Generated by: ..."*.
- **Gemini circuit breaker**: Gemini has a 15-second time limit and at most 1 retry (after 2 seconds). After a
  503, 429 or timeout, Gemini is skipped for 5 minutes, so nobody waits for an overloaded model.
- **Small requests**: Groq's free tier allows about 8,000 tokens per minute, so the app sends at most 15,000
  characters of notes per request (12,000 for chat, 8,000 for an outline). Gemini, as the backup, can get up to
  60,000 characters.
- **Saved results**: notes, outlines, quizzes, explanations, tutor scripts, chat answers and audio are saved in
  the session, so the APIs are not called again when the page reloads.
- **Friendly errors**: the app never shows error codes or raw JSON. Full errors are printed in the terminal for
  debugging.

## Database (Supabase)

QuickStudy saves each student's data in **Supabase**, under their name (typed in the welcome card on Home or in the sidebar):
uploaded chapters (with their outlines), study notes, quiz attempts and answers, reported questions, the exam
date and the daily study plan. The name is also kept in the page address (`?user=...`), so after a
refresh everything is loaded again, and Weak Topics, History and the Home stats show the saved data.
Notes and outlines that are already saved are **not** generated again, so no AI calls are wasted.

| Table | What it stores |
|-------|----------------|
| `users` | A student (`name` is unique) and their `exam_date` |
| `library_files` | Uploaded PDFs: file name, page texts, full text, outline (one per user + file name) |
| `study_notes` | AI study notes per file and language, and which AI wrote them |
| `quiz_attempts` | Each submitted quiz: chapters, settings, `normal` / `revision`, score and total |
| `answers` | Every answered question: topic, chapter, the student's answer, the correct answer, `is_correct`, `reported` |
| `study_plans` | The AI study plan of one day (one per user + date) |

Deleting a file or a user also deletes the rows that belong to it (`on delete cascade`).

### Set up the database (once)

1. Create a free project at https://supabase.com.
2. Open **SQL Editor → New query**, paste the whole of `data/schema.sql` and click **Run**.
   The script is safe to run again (it only creates tables that do not exist yet).
3. Open **Project Settings → API** and copy the **Project URL** and the **anon public** key into
   `.streamlit/secrets.toml` (see "API keys" below).

Row Level Security is turned off in `schema.sql` because this is a student prototype without logins.
Turn RLS on (with policies) before using the app in production.

### Offline mode

If Supabase is not configured or cannot be reached, QuickStudy keeps working with the current browser
session only and the sidebar shows *"Offline mode: data will not be saved"*.

## Project Structure

The code is split into layers, like a 3-tier (or MVC) web app such as Laravel:

```
quickstudy/
├── app.py                 Entry point and router only (like routes/web.php)
├── config.py              Settings: model names, text limits, languages, labels
├── state.py               All st.session_state keys in one place (init / get / set helpers)
├── assets/styles.css      All CSS
├── ui/                    Shared UI
│   ├── layout.py          Loads the CSS, the hero greeting and the sidebar
│   └── components.py      Cards, chat bubbles, badges, pills, selectors, upload card, audio tutor
├── views/                 One file per page, each with a render() function
│   ├── home.py  notes.py  ask_notes.py  quiz.py  audio_tutor.py  weak_topics.py  history.py
├── actions/               One task per file (like Laravel Action Classes), no UI code
│   ├── generate_notes.py  generate_outline.py  generate_quiz.py  explain_answers.py
│   ├── ask_question.py  generate_study_plan.py  revise_weak_topics.py
│   ├── make_tutor_script.py  manage_library.py  schemas.py (JSON formats)
│   └── sync_data.py       Loads a student's saved data and saves every change (via data/)
├── services/              Talking to AI APIs only
│   ├── ai_router.py       Groq first, Gemini as backup
│   ├── groq_client.py  gemini_client.py  tts.py  fallback_summarizer.py  secrets.py
├── data/                  Data tier: only database code (like Models/Repositories in Laravel)
│   ├── schema.sql         All Supabase tables (run once in the SQL Editor)
│   ├── client.py          Creates the Supabase client from st.secrets
│   └── repositories.py    Small functions to save and load each kind of data
├── utils/                 Small helpers: pdf_reader.py, validators.py, text.py
└── tests/                 pytest tests for utils and the AI router
```

| Tier | Folders | What it does |
|------|---------|--------------|
| **Presentation** | `views/`, `ui/`, `assets/` | What the student sees and clicks. Views only draw the page and call actions. |
| **Logic** | `actions/`, `services/` | What the app does: actions are the tasks (make a quiz, explain an answer); services talk to Groq, Gemini and gTTS. |
| **Data** | `data/` | Where data lives: Supabase tables (`schema.sql`) and the repository functions that read and write them. Actions call these functions, never the Supabase client directly. `state.py` keeps the data of the current browser session. |

The folder is called `views/`, not `pages/`, because Streamlit automatically turns a `pages/` folder into its
own navigation.

## How to install and run

You need Python 3.10 or newer.

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

The app opens in your browser at http://localhost:8501.

Run the tests with:

```bash
python -m pytest tests
```

## API keys (`.streamlit/secrets.toml`)

Create the file `.streamlit/secrets.toml` with this content and replace the placeholders with your own keys:

```toml
# Get a key at https://console.groq.com/keys
GROQ_API_KEY = "paste-your-groq-key-here"

# Get a key at https://aistudio.google.com/apikey
GEMINI_API_KEY = "paste-your-gemini-key-here"

# Supabase: Project Settings -> API (Project URL and the anon public key)
SUPABASE_URL = "paste-your-supabase-url-here"
SUPABASE_KEY = "paste-your-supabase-anon-key-here"
```

This file is listed in `.gitignore`, so your keys are never uploaded to GitHub.

If a key is missing, the app still opens. With only one key, that AI does every task (Gemini cannot be
reached without its key, so scanned PDFs need `GEMINI_API_KEY`). With no AI available, study notes come from
sumy and quizzes show a friendly message.
