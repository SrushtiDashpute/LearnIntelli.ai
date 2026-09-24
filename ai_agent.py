import os
import json
from openai import OpenAI


# ============================================================
# OPENAI CLIENT
# ============================================================

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


# ============================================================
# AI AGENT — STUDENT PERFORMANCE ANALYSIS
# ============================================================

def analyze_student(data):

    quiz_attempted = bool(data.get("quiz_attempted"))
    visual_completed = bool(data.get("visual_completed"))
    mission_attempted = bool(data.get("mission_attempted"))
    teach_back_completed = bool(data.get("teach_back_completed"))

    quiz_score = data.get("quiz_score")
    visualization_score = data.get("visualization_score")
    application_score = data.get("application_score")
    teach_back_score = data.get("teach_back_score")

    quiz_score = (
        float(quiz_score)
        if quiz_score is not None
        else None
    )

    visualization_score = (
        float(visualization_score)
        if visualization_score is not None
        else None
    )

    application_score = (
        float(application_score)
        if application_score is not None
        else None
    )

    teach_back_score = (
        float(teach_back_score)
        if teach_back_score is not None
        else None
    )


    # --------------------------------------------------------
    # NO ACTIVITY
    # --------------------------------------------------------

    if not any([
        quiz_attempted,
        visual_completed,
        mission_attempted,
        teach_back_completed
    ]):

        return {
            "learning_gap": "No Data Yet",
            "recommended_action": "Start Learning",
            "reason": (
                "The student has not completed any learning "
                "activity yet."
            )
        }


    # --------------------------------------------------------
    # APPLICATION GAP
    # --------------------------------------------------------

    if (
        mission_attempted
        and application_score is not None
        and application_score < 50
    ):

        return {
            "learning_gap": "Application Gap",
            "recommended_action": "Practice",
            "reason": (
                "The Smart Mission performance indicates that "
                "the student needs more application-based practice."
            )
        }


    # --------------------------------------------------------
    # KNOWLEDGE GAP
    # --------------------------------------------------------

    if (
        quiz_attempted
        and quiz_score is not None
        and quiz_score < 50
    ):

        return {
            "learning_gap": "Knowledge Gap",
            "recommended_action": "Revision",
            "reason": (
                "The quiz performance indicates that the student "
                "needs to strengthen the topic fundamentals."
            )
        }


    # --------------------------------------------------------
    # CONCEPTUAL GAP
    # --------------------------------------------------------

    if (
        teach_back_completed
        and teach_back_score is not None
        and teach_back_score < 50
    ):

        return {
            "learning_gap": "Conceptual Gap",
            "recommended_action": "Visual Learning",
            "reason": (
                "The Teach It Back result indicates that the student "
                "needs stronger conceptual understanding."
            )
        }


    # --------------------------------------------------------
    # VISUALIZATION GAP
    # --------------------------------------------------------

    if (
        visual_completed
        and visualization_score is not None
        and visualization_score < 50
    ):

        return {
            "learning_gap": "Visualization Gap",
            "recommended_action": "Visual Learning",
            "reason": (
                "The visual learning assessment indicates that the "
                "student needs additional visual explanation."
            )
        }


    # --------------------------------------------------------
    # NO MAJOR GAP
    # --------------------------------------------------------

    return {
        "learning_gap": "No Major Gap",
        "recommended_action": "Continue",
        "reason": (
            "The completed activities currently show satisfactory "
            "performance. AI will continue monitoring future activity."
        )
    }


# ============================================================
# AI CONTENT GENERATION
# ============================================================

def generate_learning_content(
    subject,
    standard,
    topic,
    content_type,
    difficulty,
    language,
    description,
    formula
):

    prompt = f"""
You are the AI educational content generator for LearnIntelli.

LearnIntelli is an adaptive learning platform.

The teacher can dynamically provide ANY subject, standard,
topic or concept.

Create learning content specifically for the following:

Subject: {subject}
Standard: {standard}
Topic: {topic}
Learning Type: {content_type}
Difficulty: {difficulty}
Language: {language}

Teacher Description:
{description}

Formula / Key Concept:
{formula}

IMPORTANT:
- Do NOT assume the topic is Photosynthesis.
- Generate content specifically for the provided topic.
- Keep the content suitable for the given standard.
- Make the content educational and accurate.
- The visual explanation must be specific to the topic.
- Questions must test actual understanding.
- Missions should progress from basic understanding to application.
- Return ONLY valid JSON.
- Do not use Markdown.
- Do not add explanations outside the JSON.

Return exactly this structure:

{{
    "theory": "Clear theory explanation",

    "visual": {{
        "title": "Topic-specific visual title",
        "type": "flow",
        "steps": [
            {{
                "label": "Step 1",
                "description": "Topic-specific explanation"
            }},
            {{
                "label": "Step 2",
                "description": "Topic-specific explanation"
            }},
            {{
                "label": "Step 3",
                "description": "Topic-specific explanation"
            }},
            {{
                "label": "Step 4",
                "description": "Topic-specific explanation"
            }}
        ]
    }},

    "questions": [
        {{
            "question": "Question 1",
            "options": [
                "Option A",
                "Option B",
                "Option C",
                "Option D"
            ],
            "answer": 0
        }},
        {{
            "question": "Question 2",
            "options": [
                "Option A",
                "Option B",
                "Option C",
                "Option D"
            ],
            "answer": 0
        }},
        {{
            "question": "Question 3",
            "options": [
                "Option A",
                "Option B",
                "Option C",
                "Option D"
            ],
            "answer": 0
        }},
        {{
            "question": "Question 4",
            "options": [
                "Option A",
                "Option B",
                "Option C",
                "Option D"
            ],
            "answer": 0
        }},
        {{
            "question": "Question 5",
            "options": [
                "Option A",
                "Option B",
                "Option C",
                "Option D"
            ],
            "answer": 0
        }}
    ],

    "missions": [
        {{
            "title": "Foundation mission",
            "badge": "LEVEL 1 • FOUNDATION",
            "question": "Basic understanding question",
            "options": [
                "Option A",
                "Option B",
                "Option C",
                "Option D"
            ],
            "answer": 0,
            "xp": 50
        }},
        {{
            "title": "Concept mission",
            "badge": "LEVEL 2 • CONCEPT",
            "question": "Concept understanding question",
            "options": [
                "Option A",
                "Option B",
                "Option C",
                "Option D"
            ],
            "answer": 0,
            "xp": 75
        }},
        {{
            "title": "Practice mission",
            "badge": "LEVEL 3 • PRACTICE",
            "question": "Practice-based question",
            "options": [
                "Option A",
                "Option B",
                "Option C",
                "Option D"
            ],
            "answer": 0,
            "xp": 100
        }},
        {{
            "title": "Application mission",
            "badge": "LEVEL 4 • APPLICATION",
            "question": "Application-based question",
            "options": [
                "Option A",
                "Option B",
                "Option C",
                "Option D"
            ],
            "answer": 0,
            "xp": 125
        }}
    ]
}}
"""


    # --------------------------------------------------------
    # CALL OPENAI
    # --------------------------------------------------------

    response = client.responses.create(
        model="gpt-5.6-luna",
        input=prompt
    )


    # --------------------------------------------------------
    # READ AI RESPONSE
    # --------------------------------------------------------

    result = response.output_text.strip()


    # --------------------------------------------------------
    # CONVERT JSON STRING → PYTHON DICTIONARY
    # --------------------------------------------------------

    try:

        return json.loads(result)

    except json.JSONDecodeError:

        # Sometimes AI may accidentally return code fences.
        # Remove them and try again.

        cleaned_result = result.replace(
            "```json",
            ""
        ).replace(
            "```",
            ""
        ).strip()

        return json.loads(cleaned_result)