from flask import Flask, request, jsonify
from flask_cors import CORS
from ai_agent import analyze_student, generate_learning_content
import sqlite3
import json
from datetime import datetime


app = Flask(__name__)
CORS(app)

DB_NAME = "learnintelli.db"


DEMO_STUDENTS = [
    "Krishna",
    "Srushti",
    "Manali",
    "Harshada",
    "Tanishka",
    "Khushi"
]


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# =========================================================
# DATABASE HELPERS
# =========================================================

def ensure_column(cursor, table, column, definition):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]

    if column not in columns:
        cursor.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


def init_database():

    conn = get_connection()
    cursor = conn.cursor()

    # -----------------------------------------------------
    # STUDENTS TABLE
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            concept TEXT DEFAULT 'Photosynthesis',
            quiz_score REAL,
            concept_score REAL,
            visualization_score REAL,
            application_score REAL,
            mastery REAL DEFAULT 0,
            learning_gap TEXT DEFAULT 'No Data Yet',
            recommended_action TEXT DEFAULT 'Start Learning'
        )
    """)

    # Additional student columns
    ensure_column(
        cursor,
        "students",
        "quiz_attempted",
        "INTEGER DEFAULT 0"
    )

    ensure_column(
        cursor,
        "students",
        "visual_completed",
        "INTEGER DEFAULT 0"
    )

    ensure_column(
        cursor,
        "students",
        "mission_attempted",
        "INTEGER DEFAULT 0"
    )

    ensure_column(
        cursor,
        "students",
        "mission_completed",
        "INTEGER DEFAULT 0"
    )

    ensure_column(
        cursor,
        "students",
        "teach_back_score",
        "REAL"
    )

    ensure_column(
        cursor,
        "students",
        "teach_back_completed",
        "INTEGER DEFAULT 0"
    )

    ensure_column(
        cursor,
        "students",
        "mission_xp",
        "INTEGER DEFAULT 0"
    )

    ensure_column(
        cursor,
        "students",
        "completion_percent",
        "REAL DEFAULT 0"
    )

    ensure_column(
        cursor,
        "students",
        "completed_activities",
        "INTEGER DEFAULT 0"
    )

    ensure_column(
        cursor,
        "students",
        "last_activity",
        "TEXT"
    )

    ensure_column(
        cursor,
        "students",
        "ai_reason",
        "TEXT"
    )

    # -----------------------------------------------------
    # LEARNING CONTENT TABLE
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS learning_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            standard TEXT,
            topic TEXT NOT NULL,
            description TEXT,
            difficulty TEXT,
            language TEXT DEFAULT 'English',
            formula TEXT,
            visual_explanation TEXT,
            video_url TEXT,
            questions TEXT,
            active INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # Make sure older databases also have these columns
    ensure_column(
        cursor,
        "learning_content",
        "standard",
        "TEXT"
    )

    ensure_column(
        cursor,
        "learning_content",
        "description",
        "TEXT"
    )

    ensure_column(
        cursor,
        "learning_content",
        "difficulty",
        "TEXT"
    )

    ensure_column(
        cursor,
        "learning_content",
        "language",
        "TEXT DEFAULT 'English'"
    )

    ensure_column(
        cursor,
        "learning_content",
        "formula",
        "TEXT"
    )

    ensure_column(
        cursor,
        "learning_content",
        "visual_explanation",
        "TEXT"
    )

    ensure_column(
        cursor,
        "learning_content",
        "video_url",
        "TEXT"
    )

    ensure_column(
        cursor,
        "learning_content",
        "questions",
        "TEXT"
    )

    ensure_column(
        cursor,
        "learning_content",
        "active",
        "INTEGER DEFAULT 1"
    )

    ensure_column(
        cursor,
        "learning_content",
        "created_at",
        "TEXT"
    )

    # -----------------------------------------------------
    # DEMO STUDENTS
    # -----------------------------------------------------

    for student_name in DEMO_STUDENTS:

        cursor.execute(
            """
            INSERT OR IGNORE INTO students
            (name, concept)
            VALUES (?, ?)
            """,
            (student_name, "Photosynthesis")
        )

    conn.commit()
    conn.close()


# =========================================================
# STUDENT HELPERS
# =========================================================

def fetch_student(
    conn,
    student_id=None,
    student_name=None
):

    cursor = conn.cursor()

    if student_id is not None:

        cursor.execute(
            """
            SELECT *
            FROM students
            WHERE id = ?
            """,
            (student_id,)
        )

    elif student_name:

        cursor.execute(
            """
            SELECT *
            FROM students
            WHERE LOWER(name) = LOWER(?)
            """,
            (student_name,)
        )

    else:
        return None

    return cursor.fetchone()


def calculate_metrics(student):

    scores = []

    if student["quiz_attempted"] and student["quiz_score"] is not None:
        scores.append(float(student["quiz_score"]))

    if student["visual_completed"] and student["visualization_score"] is not None:
        scores.append(float(student["visualization_score"]))

    if student["mission_attempted"] and student["application_score"] is not None:
        scores.append(float(student["application_score"]))

    if student["teach_back_completed"] and student["teach_back_score"] is not None:
        scores.append(float(student["teach_back_score"]))

    if scores:
        mastery = sum(scores) / len(scores)
    else:
        mastery = 0

    completed_activities = len(scores)

    completion_percent = (
        completed_activities / 4
    ) * 100

    return {
        "mastery": round(mastery, 2),
        "completion_percent": round(completion_percent, 2),
        "completed_activities": completed_activities
    }


def update_student_metrics(conn, student_id):

    cursor = conn.cursor()

    student = fetch_student(
        conn,
        student_id=student_id
    )

    if student is None:
        return None

    metrics = calculate_metrics(student)

    cursor.execute(
        """
        UPDATE students
        SET mastery = ?,
            completion_percent = ?,
            completed_activities = ?
        WHERE id = ?
        """,
        (
            metrics["mastery"],
            metrics["completion_percent"],
            metrics["completed_activities"],
            student_id
        )
    )

    conn.commit()

    return fetch_student(
        conn,
        student_id=student_id
    )


# =========================================================
# AI AGENT ANALYSIS
# =========================================================
@app.route("/api/ai-agent/generate-content", methods=["POST"])
def generate_content():

    data = request.get_json() or {}

    subject = data.get("subject", "")
    standard = data.get("standard", "")
    topic = data.get("topic", "")
    content_type = data.get("type", "Concept")
    difficulty = data.get("difficulty", "Medium")
    language = data.get("language", "English")
    description = data.get("description", "")
    formula = data.get("formula", "")

    if not subject or not standard or not topic:
        return jsonify({
            "success": False,
            "error": "Subject, standard and topic are required."
        }), 400

    try:

        generated = generate_learning_content(
            subject,
            standard,
            topic,
            content_type,
            difficulty,
            language,
            description,
            formula
        )

        return jsonify({
            "success": True,
            "content": generated
        })

    except Exception as e:

        print("AI CONTENT ERROR:", repr(e), flush=True)

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    
@app.route(
    "/api/ai-agent/analyze",
    methods=["POST"]
)
def analyze():

    data = request.get_json(silent=True) or {}

    student_id = data.get("student_id")
    student_name = data.get(
        "student_name",
        "Krishna"
    )

    concept = data.get("concept")
    activity_type = data.get("activity_type")

    conn = get_connection()
    cursor = conn.cursor()

    # -----------------------------------------------------
    # FIND STUDENT
    # -----------------------------------------------------

    student = fetch_student(
        conn,
        student_id=student_id,
        student_name=student_name
    )

    # -----------------------------------------------------
    # CREATE STUDENT IF NOT FOUND
    # -----------------------------------------------------

    if student is None:

        cursor.execute(
            """
            INSERT INTO students
            (name, concept)
            VALUES (?, ?)
            """,
            (
                student_name,
                concept or "Photosynthesis"
            )
        )

        conn.commit()

        student = fetch_student(
            conn,
            student_name=student_name
        )

    actual_student_id = student["id"]

    # -----------------------------------------------------
    # UPDATE CONCEPT
    # -----------------------------------------------------

    if concept:

        cursor.execute(
            """
            UPDATE students
            SET concept = ?
            WHERE id = ?
            """,
            (
                concept,
                actual_student_id
            )
        )

    # -----------------------------------------------------
    # QUIZ ACTIVITY
    # -----------------------------------------------------

    if activity_type == "quiz":

        score = data.get("quiz_score")

        if score is not None:

            score = max(
                0,
                min(
                    100,
                    float(score)
                )
            )

            cursor.execute(
                """
                UPDATE students
                SET quiz_score = ?,
                    concept_score = ?,
                    quiz_attempted = 1,
                    last_activity = ?
                WHERE id = ?
                """,
                (
                    score,
                    score,
                    datetime.now().isoformat(),
                    actual_student_id
                )
            )

    # -----------------------------------------------------
    # VISUAL ACTIVITY
    # -----------------------------------------------------

    elif activity_type == "visual":

        cursor.execute(
            """
            UPDATE students
            SET visualization_score = 100,
                visual_completed = 1,
                last_activity = ?
            WHERE id = ?
            """,
            (
                datetime.now().isoformat(),
                actual_student_id
            )
        )

    # -----------------------------------------------------
    # SMART MISSION
    # -----------------------------------------------------

    elif activity_type == "mission":

        score = data.get("application_score")
        xp = data.get("mission_xp", 0)

        if score is not None:

            score = max(
                0,
                min(
                    100,
                    float(score)
                )
            )

            mission_completed = 1 if score >= 100 else 0

            cursor.execute(
                """
                UPDATE students
                SET application_score = ?,
                    mission_attempted = 1,
                    mission_completed = ?,
                    mission_xp = ?,
                    last_activity = ?
                WHERE id = ?
                """,
                (
                    score,
                    mission_completed,
                    int(xp),
                    datetime.now().isoformat(),
                    actual_student_id
                )
            )

    # -----------------------------------------------------
    # TEACH IT BACK
    # -----------------------------------------------------

    elif activity_type == "teach_back":

        score = data.get("teach_back_score")

        if score is not None:

            score = max(
                0,
                min(
                    100,
                    float(score)
                )
            )

            cursor.execute(
                """
                UPDATE students
                SET teach_back_score = ?,
                    teach_back_completed = 1,
                    last_activity = ?
                WHERE id = ?
                """,
                (
                    score,
                    datetime.now().isoformat(),
                    actual_student_id
                )
            )

    conn.commit()

    # -----------------------------------------------------
    # UPDATE METRICS
    # -----------------------------------------------------

    student = update_student_metrics(
        conn,
        actual_student_id
    )

    # -----------------------------------------------------
    # PREPARE AI INPUT
    # -----------------------------------------------------

    ai_input = {
        "quiz_attempted": bool(
            student["quiz_attempted"]
        ),
        "visual_completed": bool(
            student["visual_completed"]
        ),
        "mission_attempted": bool(
            student["mission_attempted"]
        ),
        "teach_back_completed": bool(
            student["teach_back_completed"]
        ),
        "quiz_score": student["quiz_score"],
        "visualization_score": student["visualization_score"],
        "application_score": student["application_score"],
        "teach_back_score": student["teach_back_score"]
    }

    # -----------------------------------------------------
    # AI ANALYSIS
    # -----------------------------------------------------

    agent_result = analyze_student(
        ai_input
    )

    # -----------------------------------------------------
    # SAVE AI RESULT
    # -----------------------------------------------------

    cursor.execute(
        """
        UPDATE students
        SET learning_gap = ?,
            recommended_action = ?,
            ai_reason = ?
        WHERE id = ?
        """,
        (
            agent_result.get(
                "learning_gap",
                "No Data Yet"
            ),
            agent_result.get(
                "recommended_action",
                "Start Learning"
            ),
            agent_result.get(
                "reason",
                ""
            ),
            actual_student_id
        )
    )

    conn.commit()

    student = fetch_student(
        conn,
        student_id=actual_student_id
    )

    conn.close()

    return jsonify({
        "status": "success",
        "student_id": actual_student_id,
        "agent_result": agent_result,
        "student": dict(student)
    })


# =========================================================
# TEACH IT BACK
# =========================================================

@app.route(
    "/api/ai-agent/teach-back",
    methods=["POST"]
)
def teach_back():

    data = request.get_json(silent=True) or {}

    student_id = data.get("student_id")
    student_name = data.get(
        "student_name",
        "Krishna"
    )

    concept = data.get(
        "concept",
        "Photosynthesis"
    )

    explanation = data.get(
        "explanation",
        ""
    )

    keywords = data.get(
        "keywords",
        []
    )

    # -----------------------------------------------------
    # KEYWORDS CAN COME AS JSON STRING
    # -----------------------------------------------------

    if isinstance(keywords, str):

        try:
            keywords = json.loads(keywords)

        except json.JSONDecodeError:
            keywords = [
                item.strip()
                for item in keywords.split(",")
                if item.strip()
            ]

    if not isinstance(keywords, list):
        keywords = []

    # -----------------------------------------------------
    # PHOTOSYNTHESIS FALLBACK
    # -----------------------------------------------------

    if (
        not keywords
        and concept.lower() == "photosynthesis"
    ):

        keywords = [
            "sunlight",
            "carbon dioxide",
            "water",
            "glucose",
            "oxygen",
            "chlorophyll"
        ]

    explanation_lower = explanation.lower()

    matched_keywords = []

    for keyword in keywords:

        if str(keyword).lower() in explanation_lower:
            matched_keywords.append(
                keyword
            )

    # -----------------------------------------------------
    # SCORE
    # -----------------------------------------------------

    if keywords:

        score = (
            len(matched_keywords)
            / len(keywords)
        ) * 100

    else:
        score = 0

    score = round(score, 2)

    # -----------------------------------------------------
    # RESULT
    # -----------------------------------------------------

    if score >= 80:

        learning_gap = "No Major Gap"
        recommended_action = "Continue"
        feedback = (
            "Strong understanding demonstrated."
        )

    elif score >= 50:

        learning_gap = "Conceptual Gap"
        recommended_action = "Visual Learning"
        feedback = (
            "The student shows developing "
            "conceptual understanding."
        )

    else:

        learning_gap = "Conceptual Gap"
        recommended_action = "Visual Learning"
        feedback = (
            "The student needs stronger "
            "conceptual understanding."
        )

    missing_keywords = [
        keyword
        for keyword in keywords
        if keyword not in matched_keywords
    ]

    if missing_keywords:

        feedback += (
            " Review: "
            + ", ".join(
                str(item)
                for item in missing_keywords
            )
            + "."
        )

    # -----------------------------------------------------
    # DATABASE
    # -----------------------------------------------------

    conn = get_connection()
    cursor = conn.cursor()

    student = fetch_student(
        conn,
        student_id=student_id,
        student_name=student_name
    )

    if student is None:

        cursor.execute(
            """
            INSERT INTO students
            (name, concept)
            VALUES (?, ?)
            """,
            (
                student_name,
                concept
            )
        )

        conn.commit()

        student = fetch_student(
            conn,
            student_name=student_name
        )

    actual_student_id = student["id"]

    cursor.execute(
        """
        UPDATE students
        SET concept = ?,
            teach_back_score = ?,
            teach_back_completed = 1,
            learning_gap = ?,
            recommended_action = ?,
            ai_reason = ?,
            last_activity = ?
        WHERE id = ?
        """,
        (
            concept,
            score,
            learning_gap,
            recommended_action,
            feedback,
            datetime.now().isoformat(),
            actual_student_id
        )
    )

    conn.commit()

    student = update_student_metrics(
        conn,
        actual_student_id
    )

    conn.close()

    return jsonify({
        "status": "success",
        "student_id": actual_student_id,
        "concept": concept,
        "score": score,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "learning_gap": learning_gap,
        "recommended_action": recommended_action,
        "feedback": feedback,
        "student": dict(student)
    })


# =========================================================
# TEACHER - ADD LEARNING CONTENT
# =========================================================

@app.route(
    "/api/teacher/content",
    methods=["POST"]
)
def add_content():

    data = request.get_json(silent=True) or {}

    subject = data.get("subject")
    topic = data.get("topic")

    if not subject or not topic:

        return jsonify({
            "status": "error",
            "message": (
                "Subject and topic are required."
            )
        }), 400

    standard = data.get("standard", "")
    description = data.get("description", "")
    difficulty = data.get("difficulty", "")
    language = data.get("language", "English")
    formula = data.get("formula", "")
    visual_explanation = data.get(
        "visual_explanation",
        ""
    )
    video_url = data.get(
        "video_url",
        ""
    )

    questions = data.get(
        "questions",
        []
    )

    # -----------------------------------------------------
    # STORE QUESTIONS AS JSON
    # -----------------------------------------------------

    if isinstance(questions, (list, dict)):

        questions_json = json.dumps(
            questions
        )

    else:

        questions_json = str(
            questions
        )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO learning_content
        (
            subject,
            standard,
            topic,
            description,
            difficulty,
            language,
            formula,
            visual_explanation,
            video_url,
            questions,
            active,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            subject,
            standard,
            topic,
            description,
            difficulty,
            language,
            formula,
            visual_explanation,
            video_url,
            questions_json,
            1,
            datetime.now().isoformat()
        )
    )

    content_id = cursor.lastrowid

    conn.commit()

    cursor.execute(
        """
        SELECT *
        FROM learning_content
        WHERE id = ?
        """,
        (content_id,)
    )

    content = cursor.fetchone()

    conn.close()

    return jsonify({
        "status": "success",
        "message": "Learning content added successfully.",
        "content": dict(content)
    }), 201


# =========================================================
# TEACHER - VIEW ALL CONTENT
# =========================================================

@app.route(
    "/api/teacher/content",
    methods=["GET"]
)
def get_teacher_content():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM learning_content
        ORDER BY id DESC
        """
    )

    rows = cursor.fetchall()

    conn.close()

    return jsonify({
        "status": "success",
        "content": [
            dict(row)
            for row in rows
        ]
    })


# =========================================================
# STUDENT - AVAILABLE LEARNING CONTENT
# =========================================================

@app.route(
    "/api/learning-content",
    methods=["GET"]
)
def get_learning_content():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM learning_content
        WHERE active = 1
        ORDER BY subject, topic
        """
    )

    rows = cursor.fetchall()

    conn.close()

    return jsonify({
        "status": "success",
        "content": [
            dict(row)
            for row in rows
        ]
    })


# =========================================================
# STUDENT - SINGLE CONTENT
# =========================================================

@app.route(
    "/api/learning-content/<int:content_id>",
    methods=["GET"]
)
def get_single_learning_content(content_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM learning_content
        WHERE id = ?
        AND active = 1
        """,
        (content_id,)
    )

    row = cursor.fetchone()

    conn.close()

    if row is None:

        return jsonify({
            "status": "error",
            "message": "Learning content not found."
        }), 404

    return jsonify({
        "status": "success",
        "content": dict(row)
    })
# =========================================================
# TEACHER - ACTIVATE SELECTED LEARNING CONTENT
# =========================================================

@app.route(
    "/api/teacher/content/<int:content_id>/activate",
    methods=["POST"]
)
def activate_learning_content(content_id):

    conn = get_connection()
    cursor = conn.cursor()

    # Check if selected topic exists
    cursor.execute(
        """
        SELECT *
        FROM learning_content
        WHERE id = ?
        """,
        (content_id,)
    )

    selected_content = cursor.fetchone()

    if selected_content is None:

        conn.close()

        return jsonify({
            "status": "error",
            "message": "Learning content not found."
        }), 404


    # Make all topics inactive
    cursor.execute(
        """
        UPDATE learning_content
        SET active = 0
        """
    )


    # Make selected topic active
    cursor.execute(
        """
        UPDATE learning_content
        SET active = 1
        WHERE id = ?
        """,
        (content_id,)
    )


    conn.commit()


    # Get selected topic again
    cursor.execute(
        """
        SELECT *
        FROM learning_content
        WHERE id = ?
        """,
        (content_id,)
    )

    active_content = cursor.fetchone()

    conn.close()


    return jsonify({
        "status": "success",
        "message": "Learning topic activated successfully.",
        "content": dict(active_content)
    })

# =========================================================
# TEACHER - STUDENT PERFORMANCE
# =========================================================

@app.route(
    "/api/teacher/students",
    methods=["GET"]
)
def get_teacher_students():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM students
        ORDER BY name
        """
    )

    rows = cursor.fetchall()

    conn.close()

    return jsonify({
        "status": "success",
        "students": [
            dict(row)
            for row in rows
        ]
    })


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route(
    "/api/health",
    methods=["GET"]
)
def health_check():

    return jsonify({
        "status": "success",
        "message": "LearnIntelli backend is running."
    })


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    init_database()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )