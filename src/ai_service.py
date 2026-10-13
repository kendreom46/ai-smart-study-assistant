"""
AI Service for StudyMate AI
Integrates with Google's official 'google-genai' SDK for Gemini.
Handles topic explanations, notes summarization, structured quiz generation, and study chat.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

# Attempt to import google.genai
try:
    from google import genai
    from google.genai import types
    from google.genai.errors import APIError
except ImportError:
    genai = None  # type: ignore
    types = None  # type: ignore
    APIError = Exception  # type: ignore


# ------------------------------------------------------------------------------
# Pydantic Models for Structured Quiz Output
# ------------------------------------------------------------------------------

class QuizQuestion(BaseModel):
    question: str = Field(description="The question text.")
    option_a: str = Field(description="First multiple choice option.")
    option_b: str = Field(description="Second multiple choice option.")
    option_c: str = Field(description="Third multiple choice option.")
    option_d: str = Field(description="Fourth multiple choice option.")
    correct_answer: str = Field(
        description="The letter of the correct option: 'A', 'B', 'C', or 'D'."
    )
    explanation: str = Field(
        description="Clear academic explanation for why this answer is correct."
    )


class QuizModel(BaseModel):
    topic: str = Field(description="Topic or title of the generated quiz.")
    questions: List[QuizQuestion] = Field(description="List of multiple-choice questions.")


# ------------------------------------------------------------------------------
# Gemini AI Service Implementation
# ------------------------------------------------------------------------------

class AIService:
    """
    Service wrapper around Google Gemini API.
    Provides dependency injection for testing and comprehensive error handling.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        client: Optional[Any] = None,
    ):
        """
        Initialize the AI Service.
        Reads credentials from environment variables or explicit parameters.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        # Configurable model with a sensible, fast default
        self.model = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self._client = client

    def get_client(self) -> Any:
        """Lazily initialize and return the official google-genai Client."""
        if self._client is not None:
            return self._client

        if not self.api_key or self.api_key.strip() in ("", "your_gemini_api_key_here"):
            raise ValueError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY in your .env file "
                "or provide it in the application settings."
            )

        if genai is None:
            raise ImportError(
                "The 'google-genai' SDK is not installed. Please run: pip install google-genai"
            )

        self._client = genai.Client(api_key=self.api_key.strip())
        return self._client

    def is_configured(self) -> bool:
        """Check if an API key is present without making an API call."""
        key = self.api_key or os.getenv("GEMINI_API_KEY")
        return bool(key and key.strip() not in ("", "your_gemini_api_key_here"))

    def _sanitize_error(self, exc: Exception) -> str:
        """
        Return a student-friendly error message without leaking sensitive API keys.
        """
        raw_msg = str(exc)
        # Scrub potential API keys from error strings (AIza followed by alphanumeric/dashes)
        cleaned_msg = re.sub(r"AIza[0-9A-Za-z\-_]+", "[PROTECTED_API_KEY]", raw_msg)
        if self.api_key and len(self.api_key) > 5 and self.api_key in cleaned_msg:
            cleaned_msg = cleaned_msg.replace(self.api_key, "[PROTECTED_API_KEY]")

        if "API_KEY_INVALID" in cleaned_msg or "400" in cleaned_msg and "API key" in cleaned_msg:
            return "Authentication Error: The provided Gemini API key appears invalid. Please check your .env configuration."
        if "RESOURCE_EXHAUSTED" in cleaned_msg or "429" in cleaned_msg:
            return "Quota Exceeded: Gemini API rate limit or quota reached. Please wait a few moments before retrying."
        if "NOT_FOUND" in cleaned_msg or "model" in cleaned_msg.lower() and "not found" in cleaned_msg.lower():
            return f"Model Unavailable: Configured model '{self.model}' was not found. Try 'gemini-2.5-flash' in your .env file."
        if "connection" in cleaned_msg.lower() or "timeout" in cleaned_msg.lower():
            return "Network Error: Unable to reach Google Gemini API. Please check your internet connection."

        return f"AI Service Error: {cleaned_msg}"

    # --------------------------------------------------------------------------
    # Feature B: AI Topic Explainer
    # --------------------------------------------------------------------------
    def explain_topic(
        self,
        topic: str,
        level: str = "intermediate",
        length: str = "detailed",
        context: str = "",
    ) -> str:
        """
        Generate a pedagogical explanation of a concept or topic.
        Organized with overview, core definitions, analogies/examples, and key takeaways.
        """
        if not topic or not topic.strip():
            raise ValueError("Please provide a topic to explain.")

        level_instructions = {
            "beginner": "Explain using simple concepts, relatable analogies, and minimal jargon. Ideal for high school or freshman college level.",
            "intermediate": "Provide a balanced undergraduate-level explanation with standard technical terminology, practical real-world context, and clear rationale.",
            "advanced": "Deliver an in-depth, rigorous technical explanation covering underlying mechanisms, theoretical considerations, and edge cases.",
        }

        length_instructions = {
            "concise": "Keep the explanation focused and direct (around 250-400 words).",
            "detailed": "Provide a comprehensive, well-structured guide (around 600-900 words).",
        }

        system_prompt = (
            "You are StudyMate AI, an expert, patient university professor and study tutor. "
            "Your explanations are crystal-clear, structured, well-formatted in Markdown, and encouraging. "
            "Use clear headings, bullet points, bold key terms, and code snippets or formulas if appropriate."
        )

        user_prompt = f"""
Please explain the following academic topic:
**Topic:** {topic.strip()}

**Target Audience Level:** {level.capitalize()} ({level_instructions.get(level.lower(), level_instructions['intermediate'])})
**Depth / Length:** {length.capitalize()} ({length_instructions.get(length.lower(), length_instructions['detailed'])})

{f"**Additional Study Material / Context to Ground Explanation In:**\n{context.strip()}" if context.strip() else ""}

Format the explanation using these clear markdown sections:
1. ### 📌 Overview & Definition
2. ### 💡 Core Concepts & Mechanisms
3. ### 🔍 Concrete Example or Real-World Analogy
4. ### ⚠️ Common Pitfalls / Misconceptions
5. ### 📝 Key Takeaways for Exams
"""

        try:
            client = self.get_client()
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.4,
            )
            response = client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=config,
            )
            return response.text.strip()
        except Exception as e:
            raise RuntimeError(self._sanitize_error(e)) from e

    # --------------------------------------------------------------------------
    # Feature C: Notes Summarizer
    # --------------------------------------------------------------------------
    def summarize_notes(
        self,
        notes: str,
        summary_type: str = "detailed",
    ) -> str:
        """
        Summarize student notes while preserving essential terms and facts.
        """
        if not notes or not notes.strip():
            raise ValueError("Please provide notes to summarize.")

        type_instructions = {
            "short": (
                "Create a high-level executive summary in 2-3 concise paragraphs, highlighting the core themes."
            ),
            "detailed": (
                "Provide an organized, multi-section summary retaining all key formulas, definitions, and arguments."
            ),
            "exam_revision": (
                "Generate high-yield exam revision bullet points, categorized by topic, plus a 'Fast Facts / Formulas' table."
            ),
        }

        system_prompt = (
            "You are StudyMate AI, an academic synthesis specialist. "
            "Your task is to summarize the provided student notes faithfully without fabricating facts. "
            "Preserve specific technical terms, names, and principles found in the text."
        )

        user_prompt = f"""
Summarize the following study notes:

**Summary Objective:** {type_instructions.get(summary_type, type_instructions['detailed'])}

**Source Notes:**
\"\"\"
{notes.strip()}
\"\"\"

Please format the summary cleanly in Markdown with bold key terms and appropriate section headers.
"""

        try:
            client = self.get_client()
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
            )
            response = client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=config,
            )
            return response.text.strip()
        except Exception as e:
            raise RuntimeError(self._sanitize_error(e)) from e

    # --------------------------------------------------------------------------
    # Feature D: AI Quiz Generator
    # --------------------------------------------------------------------------
    def generate_quiz(
        self,
        study_material: str,
        num_questions: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple-choice practice quiz questions with answer keys and explanations.
        Uses structured JSON response parsing.
        """
        if not study_material or not study_material.strip():
            raise ValueError("Please provide a topic or study notes for the quiz.")

        # Cap question count safely between 1 and 20
        count = max(1, min(num_questions, 20))

        system_prompt = (
            "You are an academic examination board specialist. "
            f"Generate exactly {count} multiple-choice questions (MCQs) based on the provided material. "
            "Each question must have 4 distinct, plausible options (A, B, C, D), exactly one unambiguously correct answer, "
            "and a thorough explanation of why the correct answer is right and why others are incorrect."
        )

        user_prompt = f"""
Create a practice quiz with {count} questions for university students from this study material:

\"\"\"
{study_material.strip()[:10000]}
\"\"\"

Ensure questions test conceptual understanding rather than trivial trivia.
"""

        try:
            client = self.get_client()
            # Use structured output schema with Pydantic
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=QuizModel,
            )
            response = client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=config,
            )
            raw_text = response.text.strip()

            # Parse and validate JSON
            return self._parse_quiz_json(raw_text)

        except Exception as e:
            raise RuntimeError(self._sanitize_error(e)) from e

    def _parse_quiz_json(self, json_text: str) -> List[Dict[str, Any]]:
        """
        Parse raw JSON into a standardized list of question dictionaries.
        Robust to code blocks or surrounding text.
        """
        clean_text = json_text.strip()
        # Strip markdown fences if present
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?\n?", "", clean_text)
            clean_text = re.sub(r"\n?```$", "", clean_text)

        data = json.loads(clean_text)
        raw_questions = data.get("questions", []) if isinstance(data, dict) else data

        formatted_questions = []
        for idx, q in enumerate(raw_questions):
            # Normalize correct answer to uppercase letter
            correct = str(q.get("correct_answer", "A")).strip().upper()
            if correct not in ("A", "B", "C", "D"):
                correct = "A"

            # Options dictionary
            options = {
                "A": str(q.get("option_a", q.get("options", {}).get("A", "Option A"))),
                "B": str(q.get("option_b", q.get("options", {}).get("B", "Option B"))),
                "C": str(q.get("option_c", q.get("options", {}).get("C", "Option C"))),
                "D": str(q.get("option_d", q.get("options", {}).get("D", "Option D"))),
            }

            formatted_questions.append({
                "id": idx + 1,
                "question": str(q.get("question", f"Question {idx + 1}")),
                "options": options,
                "correct_answer": correct,
                "explanation": str(q.get("explanation", "No explanation provided.")),
            })

        if not formatted_questions:
            raise ValueError("The AI model did not return any questions in the expected format.")

        return formatted_questions

    # --------------------------------------------------------------------------
    # Feature E: Study Chat Assistant
    # --------------------------------------------------------------------------
    def chat_response(
        self,
        messages: List[Dict[str, str]],
        user_prompt: str,
        pdf_context: str = "",
    ) -> str:
        """
        Generate a conversational study response given conversation history and optional PDF context.
        """
        if not user_prompt or not user_prompt.strip():
            raise ValueError("Please provide a question or message.")

        system_instruction = (
            "You are StudyMate AI, an approachable, highly knowledgeable academic tutor. "
            "You assist students with homework understanding, coding problems, exam prep, and concept clarification. "
            "Always be pedagogical, structure complex answers clearly, and provide examples."
        )

        if pdf_context.strip():
            system_instruction += (
                "\n\nIMPORTANT DOCUMENT GROUNDING INSTRUCTIONS:\n"
                "The student has provided an attached study document/PDF. "
                "Base your response primarily on the document content provided below. "
                "Explicitly cite or reference the document where appropriate. "
                "If the answer is NOT found within the provided document text, clearly state: "
                "'This information is not mentioned in your uploaded document,' and then provide a general explanation if helpful."
            )

        # Assemble conversation context
        formatted_contents: List[types.Content] = []

        if pdf_context.strip():
            formatted_contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text=f"=== ATTACHED STUDY DOCUMENT CONTEXT ===\n{pdf_context.strip()[:15000]}\n=== END DOCUMENT CONTEXT ==="
                        )
                    ],
                )
            )
            formatted_contents.append(
                types.Content(
                    role="model",
                    parts=[
                        types.Part.from_text(
                            text="I have reviewed your attached study document. How can I help you understand or study this material?"
                        )
                    ],
                )
            )

        # Add recent turns (up to last 10 messages for context stability)
        for msg in messages[-10:]:
            role = "user" if msg.get("role") == "user" else "model"
            content = msg.get("content", "")
            if content.strip():
                formatted_contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=content.strip())],
                    )
                )

        # Add current user prompt
        formatted_contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_prompt.strip())],
            )
        )

        try:
            client = self.get_client()
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.4,
            )
            response = client.models.generate_content(
                model=self.model,
                contents=formatted_contents,
                config=config,
            )
            return response.text.strip()
        except Exception as e:
            raise RuntimeError(self._sanitize_error(e)) from e
