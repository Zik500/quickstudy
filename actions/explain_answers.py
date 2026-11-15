"""Action: "Explain more" for one wrong answer (only when the student asks for it)."""

from actions.schemas import DetailedExplanation
from config import GROQ_MAIN, MAX_GEMINI_CHARS, MAX_GROQ_CHARS, POSSIBLE_ERROR
from services.ai_router import ask_ai_json
from utils.text import clean_explanation, trim_text


def explanation_prompt(notes: str, question: dict, chosen: int) -> list[dict]:
    """Chat messages asking for a short, final-answer explanation + a quote from the notes."""
    rules = f"""You explain quiz mistakes to a student, using ONLY the lecture notes.
Reply ONLY with JSON: {{"explanation": "...", "quote": "..."}}
- "explanation": 2-3 short sentences. Say why the student's answer is wrong and why the correct
  answer is right. Give the final answer only: never show your working or words like "Wait" or "Actually".
- If you believe the answer key is wrong, the explanation must start with "{POSSIBLE_ERROR}"
  and say briefly what the notes suggest instead. Never defend a wrong answer key.
- "quote": a short passage (1-3 sentences) copied word-for-word from the notes that supports the
  correct answer, or "" if there is none."""
    content = (
        f"Question: {question['question']}\n"
        f"Options: {question['options']}\n"
        f"Student's answer: {question['options'][chosen]}\n"
        f"Answer key: {question['answer']}\n\n"
        f"NOTES:\n{notes}"
    )
    return [{"role": "system", "content": rules}, {"role": "user", "content": content}]


def explain_more(notes: str, question: dict, chosen: int) -> dict:
    """Detailed explanation of one wrong answer (main Groq model, Gemini as backup).
    Returns {"explanation", "quote", "generated_by"}."""
    result, label = ask_ai_json(
        explanation_prompt(trim_text(notes, MAX_GROQ_CHARS), question, chosen),
        max_tokens=1500,
        schema=DetailedExplanation,
        model=GROQ_MAIN,
        reasoning_effort="medium",
        backup_messages=explanation_prompt(trim_text(notes, MAX_GEMINI_CHARS), question, chosen),
    )
    explanation = clean_explanation(result.explanation) or question["explanation"]
    return {"explanation": explanation, "quote": result.quote.strip(), "generated_by": label}
