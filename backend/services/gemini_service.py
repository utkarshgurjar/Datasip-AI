"""
DataSip Gemini Service
Centralized wrapper for all Google Gemini AI calls:
  - chat_reply()           : adaptive AI tutor chat
  - generate_quiz()        : structured JSON quiz generation
  - generate_learning_path(): personalized learning roadmap
  - explain_answer()       : per-question explanation
"""
import json
import logging
import re
from typing import List, Dict, Optional, Any
import google.generativeai as genai
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Configure the Gemini SDK once at import time
genai.configure(api_key=settings.gemini_api_key)


def _get_model(json_mode: bool = False) -> genai.GenerativeModel:
    """Return a configured GenerativeModel instance."""
    if json_mode:
        generation_config = genai.types.GenerationConfig(
            temperature=0.4,
            max_output_tokens=8192,
            response_mime_type="application/json",
        )
    else:
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            max_output_tokens=8192,
        )
    return genai.GenerativeModel(
        model_name=settings.model_name,
        generation_config=generation_config,
    )


def _safe_json_parse(text: str) -> Optional[Any]:
    """
    Try to parse JSON from a Gemini response.
    Handles cases where the model wraps JSON in markdown code fences.
    """
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
    try:
        return json.loads(cleaned.strip())
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse failed: {e}\nRaw text: {text[:500]}")
        return None


# ─────────────────────────── CHAT ───────────────────────────

def _build_system_prompt(user_profile: Dict[str, Any], weak_topics: List[str]) -> str:
    """Build an adaptive system prompt based on user's learning profile."""
    name       = user_profile.get("name", "Student")
    level      = user_profile.get("education_level", "intermediate")
    style      = user_profile.get("learning_style", "reading")
    interests  = user_profile.get("interests", "general topics")
    goal       = user_profile.get("goal", "learn effectively")
    topics_str = ", ".join(weak_topics or []) or "none identified yet"

    if style == "visual":
        style_instruction = "use visual diagrams and analogies to explain concepts"
    elif style == "practice":
        style_instruction = "give hands-on examples and practice problems"
    else:
        style_instruction = "provide clear, structured written explanations"

    return (
        f"You are DataSip AI Tutor — an expert, encouraging, and adaptive learning assistant.\n\n"
        f"Student Profile:\n"
        f"- Name: {name}\n"
        f"- Education Level: {level}\n"
        f"- Learning Style: {style}\n"
        f"- Interests: {interests}\n"
        f"- Current Goal: {goal}\n"
        f"- Weak Topics: {topics_str}\n\n"
        f"Instructions:\n"
        f"1. Adapt your explanations to the student's education level ({level}).\n"
        f"2. For '{style}' learners: {style_instruction}.\n"
        f"3. Focus on their weak topics when relevant: {topics_str}\n"
        f"4. Use markdown formatting: **bold** for key terms, `code` for code, numbered lists for steps.\n"
        f"5. Always be encouraging and positive.\n"
        f"6. If asked to 'explain simpler', give a more basic explanation using analogies.\n"
        f"7. Keep responses concise but complete. Use examples that connect to their interests: {interests}.\n"
    )


def chat_reply(
    messages: List[Dict[str, str]],
    user_profile: Dict[str, Any],
    weak_topics: List[str] = None,
) -> str:
    """
    Generate an AI tutor reply given conversation history and user profile.

    Args:
        messages: List of {"role": "user"|"model", "parts": [text]} dicts
        user_profile: Dict with user's name, education_level, learning_style, etc.
        weak_topics: List of topic strings where user scores < 60%

    Returns:
        Assistant reply string, or a graceful fallback on error.
    """
    try:
        system_prompt = _build_system_prompt(user_profile, weak_topics or [])

        model = genai.GenerativeModel(
            model_name=settings.model_name,
            system_instruction=system_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=4096,
            ),
        )

        # Build Gemini history (all messages except the last user message)
        history      = messages[:-1] if len(messages) > 1 else []
        last_message = messages[-1]["parts"][0] if messages else ""

        chat     = model.start_chat(history=history)
        response = chat.send_message(last_message)
        return response.text

    except Exception as e:
        logger.error(f"chat_reply error: {e}")
        return (
            "I'm having trouble connecting right now. Please try again in a moment. "
            "In the meantime, feel free to rephrase your question!"
        )


# ─────────────────────────── QUIZ GENERATION ───────────────────────────

def _difficulty_description(difficulty: str) -> str:
    if difficulty == "beginner":
        return "basic concepts and definitions"
    elif difficulty == "advanced":
        return "advanced analysis and synthesis"
    return "intermediate understanding and application"


QUIZ_PROMPT_TEMPLATE = """\
Generate a quiz with EXACTLY {num_questions} questions about "{topic}" at {difficulty} level.

Question types to generate: {q_type_instruction}

Return ONLY valid JSON in this exact format:
{{
  "topic": "{topic}",
  "difficulty": "{difficulty}",
  "questions": [
    {{
      "question_text": "The question here",
      "question_type": "mcq",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option A",
      "explanation": "Detailed explanation of why this is correct"
    }}
  ]
}}

Rules:
- For MCQ: provide exactly 4 options
- For true_false: options must be exactly ["True", "False"]
- correct_answer must EXACTLY match one of the options
- Explanations should be educational and 1-3 sentences
- Questions must be clear, unambiguous, and test real knowledge
- Difficulty {difficulty}: {difficulty_desc}
"""

Q_TYPE_INSTRUCTIONS = {
    "mcq":        "All questions should be multiple-choice (4 options each)",
    "true_false": "All questions should be True/False",
    "mixed":      "Mix of multiple-choice and True/False questions",
}


def generate_quiz(
    topic: str,
    difficulty: str = "intermediate",
    num_questions: int = 5,
    question_type: str = "mcq",
) -> Optional[Dict[str, Any]]:
    """
    Generate a quiz using Gemini with JSON output mode.
    Retries once on JSON parse failure.

    Returns parsed quiz dict or None on failure.
    """
    prompt = QUIZ_PROMPT_TEMPLATE.format(
        topic=topic,
        difficulty=difficulty,
        num_questions=num_questions,
        q_type_instruction=Q_TYPE_INSTRUCTIONS.get(question_type, Q_TYPE_INSTRUCTIONS["mcq"]),
        difficulty_desc=_difficulty_description(difficulty),
    )

    for attempt in range(2):  # Retry once on failure
        try:
            model    = _get_model(json_mode=True)
            response = model.generate_content(prompt)
            parsed   = _safe_json_parse(response.text)

            if parsed and "questions" in parsed:
                questions = parsed["questions"]
                if len(questions) == 0:
                    logger.warning(f"Quiz attempt {attempt+1}: no questions in response")
                    continue
                return parsed
            else:
                logger.warning(f"Quiz attempt {attempt+1}: invalid structure")

        except Exception as e:
            logger.error(f"generate_quiz attempt {attempt+1} error: {e}")

    return None


# ─────────────────────────── LEARNING PATH ───────────────────────────

LEARNING_PATH_PROMPT = """\
Create a personalized learning roadmap for a student.

Student Profile:
- Goal: {goal}
- Education Level: {level}
- Weak Topics (needs improvement): {weak_topics}
- Learning Style: {style}

Generate a step-by-step learning path with 5-8 modules.

Return ONLY valid JSON:
{{
  "goal": "{goal}",
  "total_estimated_time": "X weeks",
  "steps": [
    {{
      "order": 1,
      "title": "Module title",
      "description": "What this module covers and why it's important",
      "subtopics": ["subtopic1", "subtopic2", "subtopic3"],
      "estimated_time": "X hours",
      "resources": [
        {{"title": "Resource name", "url": "https://example.com", "type": "article"}},
        {{"title": "Video tutorial", "url": "https://youtube.com", "type": "video"}}
      ]
    }}
  ]
}}

Resource types: article, video, exercise, book, course
Make sure weak topics ({weak_topics}) are addressed early in the path.
Resources should be real, well-known educational resources (Khan Academy, MDN, freeCodeCamp, Coursera, etc.)
"""


def generate_learning_path(
    goal: str,
    level: str = "intermediate",
    weak_topics: List[str] = None,
    learning_style: str = "reading",
) -> Optional[Dict[str, Any]]:
    """
    Generate a personalized learning path using Gemini.

    Returns parsed path dict or None on failure.
    """
    weak_str = ", ".join(weak_topics or []) or "none yet"
    prompt = LEARNING_PATH_PROMPT.format(
        goal=goal,
        level=level,
        weak_topics=weak_str,
        style=learning_style,
    )

    for attempt in range(2):
        try:
            model    = _get_model(json_mode=True)
            response = model.generate_content(prompt)
            parsed   = _safe_json_parse(response.text)

            if parsed and "steps" in parsed and len(parsed["steps"]) > 0:
                return parsed
            else:
                logger.warning(f"Learning path attempt {attempt+1}: invalid structure")

        except Exception as e:
            logger.error(f"generate_learning_path attempt {attempt+1} error: {e}")

    return None


# ─────────────────────────── EXPLAIN ANSWER ───────────────────────────

def explain_answer(
    question_text: str,
    correct_answer: str,
    user_answer: str,
    topic: str = "",
) -> str:
    """
    Generate a detailed explanation for a quiz question result.

    Returns explanation string or a default message on failure.
    """
    try:
        is_correct = user_answer.strip().lower() == correct_answer.strip().lower()
        status     = "correctly" if is_correct else "incorrectly"
        follow_up  = (
            "Reinforce why this answer is correct."
            if is_correct
            else f"Explain why '{user_answer}' is incorrect and what the student should understand instead."
        )

        prompt = (
            f"A student answered a quiz question {status}.\n\n"
            f"Question: {question_text}\n"
            f"Correct Answer: {correct_answer}\n"
            f"Student's Answer: {user_answer}\n"
            f"Topic: {topic}\n\n"
            f"Provide a clear, educational explanation (2-4 sentences):\n"
            f"1. Why '{correct_answer}' is the correct answer\n"
            f"2. {follow_up}\n\n"
            f"Be encouraging and educational."
        )

        model    = _get_model(json_mode=False)
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        logger.error(f"explain_answer error: {e}")
        return f"The correct answer is: {correct_answer}."
