"""Pydantic schemas for the JSON the AI must return."""

from pydantic import BaseModel, Field


class Question(BaseModel):
    question: str
    options: list[str] = Field(description="Exactly 4 different answer choices.")
    answer: str = Field(description="The correct option, copied exactly from options.")
    topic: str = Field(description="Short topic name, 2-5 words, e.g. 'Defect Rejection Ratio'.")
    chapter: str = Field(description="The chapter name from the '=== CHAPTER' heading.")
    explanation: str = Field(description="1-2 short sentences with the final reason. No thinking aloud.")


class Quiz(BaseModel):
    questions: list[Question]


class DetailedExplanation(BaseModel):
    explanation: str = Field(description="2-3 short sentences: why the chosen answer is wrong and the right one is right.")
    quote: str = Field(description="A short word-for-word passage from the notes that supports the correct answer.")


class PageTexts(BaseModel):
    pages: list[str] = Field(description="The text of each page, in order.")
