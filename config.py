"""App settings: model names, text limits, languages and labels. Secrets stay in st.secrets."""

# ---------- AI models ----------
# Groq is the PRIMARY AI (fast, higher free limits). Gemini is the backup for every task + vision.
GROQ_MAIN = "openai/gpt-oss-120b"  # study notes, outline, quiz, revision quiz, study plan, "Explain more"
GROQ_FAST = "openai/gpt-oss-20b"   # Ask Notes chat, Audio Tutor scripts
GEMINI = "gemini-3.8-flash"        # backup for every Groq task + reading scanned PDFs (vision)

GROQ_TIMEOUT_SECONDS = 20       # then the task goes to Gemini
GEMINI_TIMEOUT_SECONDS = 15     # time limit per Gemini attempt
GEMINI_RETRY_WAITS = [2]        # Gemini gets at most 1 retry, after 2 seconds
GEMINI_COOLDOWN_SECONDS = 300   # after a 503 / 429 / timeout, skip Gemini for 5 minutes

# ---------- Text limits ----------
MAX_GROQ_CHARS = 15_000         # Groq free tier allows 8K tokens/minute (~4 characters per token)
MAX_GEMINI_CHARS = 60_000       # Gemini (backup) accepts longer prompts, e.g. full-PDF quizzes
MAX_CHAT_NOTES_CHARS = 12_000   # notes sent with each chat question
MAX_CHAT_MESSAGES = 6           # only the most recent chat messages are sent
MAX_OUTLINE_CHARS = 8_000       # text sent for a chapter outline (small, to save tokens)
FALLBACK_SENTENCES = 10         # sentences in the sumy fallback summary

# ---------- Scanned PDFs (Gemini Vision) ----------
MIN_CHARS_PER_PAGE = 200        # less text than this per page (on average) = probably a scanned PDF
VISION_MAX_PAGES = 10           # only the first 10 pages are read with Gemini Vision

# ---------- Quiz ----------
DIFFICULTIES = ["Easy", "Medium", "Hard"]
QUESTION_COUNTS = [5, 10]
REVISION_QUESTIONS = 5
QUIZ_SOURCES = ["Study notes (fast)", "Full PDF (detailed)"]
DIFFICULTY_HINTS = {
    "Easy": "Easy: test basic definitions and facts stated directly in the notes.",
    "Medium": "Medium: test understanding, e.g. comparing ideas or explaining why.",
    "Hard": "Hard: test application, e.g. short scenarios where the student must apply the ideas.",
}
POSSIBLE_ERROR = "This question may contain an error."

# ---------- Languages and fixed chat phrases ----------
LANGUAGES = {"English": "en", "Bahasa Melayu": "ms"}  # language name -> gTTS code
NOT_COVERED = {
    "English": "This is not covered in your notes.",
    "Bahasa Melayu": "Perkara ini tidak dibincangkan dalam nota anda.",
}
WHICH_PART = {
    "English": "Which part do you want me to explain?",
    "Bahasa Melayu": "Bahagian mana yang anda mahu saya terangkan?",
}
OVERVIEW = {
    "English": "Quick overview of everything",
    "Bahasa Melayu": "Gambaran ringkas keseluruhan",
}
FOLLOW_UP = {
    "English": "Want me to explain another part or give you a quick question to test yourself?",
    "Bahasa Melayu": "Mahu saya terangkan bahagian lain atau beri soalan ringkas untuk menguji diri anda?",
}
TUTOR_STYLE = (
    "You are a friendly teacher talking directly to one student. "
    "Write in {language}. Write plain spoken text only: no Markdown, no bullet points, "
    "no headings, no emojis, no lists. Use simple words and short sentences."
)

# ---------- Navigation ----------
PAGES = {
    "Home": ":material/home:",
    "Notes": ":material/description:",
    "Ask Notes": ":material/forum:",
    "Quiz": ":material/quiz:",
    "Audio Tutor": ":material/headphones:",
    "Weak Topics": ":material/insights:",
    "History": ":material/history:",
}

# Quick action cards on the Home page: (label, icon, page it opens)
QUICK_ACTIONS = [
    ("Generate study notes", ":material/edit_note:", "Notes"),
    ("Take a quiz", ":material/quiz:", "Quiz"),
    ("Audio tutor", ":material/headphones:", "Audio Tutor"),
    ("Review weak topics", ":material/insights:", "Weak Topics"),
]

# Study plan actions: label, icon and the page each one opens
PLAN_ACTIONS = {
    "notes": ("Open notes", ":material/description:", "Notes"),
    "quiz": ("Take quiz", ":material/quiz:", "Quiz"),
    "audio": ("Listen", ":material/headphones:", "Audio Tutor"),
    "revise": ("Revise", ":material/autorenew:", "Weak Topics"),
    "ask": ("Ask", ":material/forum:", "Ask Notes"),
}
