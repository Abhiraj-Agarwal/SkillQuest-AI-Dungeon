"""
Mock AI endpoints — used when USE_MOCK_AI=true or before P3 delivers real endpoints.
"""
import uuid
from fastapi import APIRouter

router = APIRouter(prefix="/ai", tags=["AI (Mock)"])

# Hardcoded mock questions per topic
MOCK_QUESTIONS = {
    "arrays": {
        "question": "What is the time complexity of accessing an element in an array by its index?",
        "expected_answer": "O(1) constant time because arrays provide direct access via memory address calculation",
        "hint": "Think about how memory addressing works with contiguous storage."
    },
    "linked_lists": {
        "question": "What is the main advantage of a linked list over an array for insertion operations?",
        "expected_answer": "Linked lists allow O(1) insertion at the head or at a known position without shifting elements, unlike arrays which require O(n) shifting",
        "hint": "Consider what happens to other elements when you insert in the middle."
    },
    "stacks_queues": {
        "question": "Explain the difference between a stack and a queue in terms of element ordering.",
        "expected_answer": "A stack follows LIFO (Last In First Out) ordering while a queue follows FIFO (First In First Out) ordering",
        "hint": "Think of a stack of plates vs a line at a store."
    },
    "binary_search": {
        "question": "What is the time complexity of binary search and what prerequisite must the data satisfy?",
        "expected_answer": "Binary search has O(log n) time complexity and requires the data to be sorted",
        "hint": "The algorithm eliminates half the search space each step."
    },
    "recursion": {
        "question": "What are the two essential components every recursive function must have?",
        "expected_answer": "A base case that stops the recursion and a recursive case that calls the function with a smaller subproblem moving toward the base case",
        "hint": "Without one of these, you get infinite recursion."
    },
    "trees": {
        "question": "What is the maximum number of nodes at level k in a binary tree?",
        "expected_answer": "2^k nodes, where the root is at level 0",
        "hint": "Each level doubles the maximum possible nodes."
    },
    "binary_search_tree": {
        "question": "What property must a Binary Search Tree maintain for all nodes?",
        "expected_answer": "For every node, all values in its left subtree must be less than the node's value, and all values in its right subtree must be greater",
        "hint": "It's related to the ordering of elements."
    },
    "heaps": {
        "question": "What is the time complexity of extracting the minimum element from a min-heap?",
        "expected_answer": "O(log n) because after removing the root, the heap must be restored by sifting down through at most log n levels",
        "hint": "The min is always at the root, but maintaining the heap property takes work."
    },
    "graphs": {
        "question": "What is the difference between BFS and DFS in terms of the data structure used?",
        "expected_answer": "BFS uses a queue to explore nodes level by level, while DFS uses a stack (or recursion) to explore as deep as possible before backtracking",
        "hint": "One goes wide, the other goes deep."
    },
    "dynamic_programming": {
        "question": "What two properties must a problem have to be solvable using dynamic programming?",
        "expected_answer": "Optimal substructure (optimal solution can be built from optimal solutions of subproblems) and overlapping subproblems (same subproblems are solved multiple times)",
        "hint": "Think about why memoization helps."
    },
    "sorting_algorithms": {
        "question": "What is the best-case and worst-case time complexity of quicksort?",
        "expected_answer": "Best case is O(n log n) when the pivot divides the array roughly in half each time. Worst case is O(n^2) when the pivot is always the smallest or largest element",
        "hint": "The pivot selection is key."
    },
}


@router.post("/question/generate")
async def mock_generate_question(body: dict):
    """Mock: returns a hardcoded question for the given topic."""
    topic = body.get("topic", "arrays")
    difficulty = body.get("difficulty", "medium")

    q = MOCK_QUESTIONS.get(topic, MOCK_QUESTIONS["arrays"])
    question_id = str(uuid.uuid4())

    return {
        "question_id": question_id,
        "question": q["question"],
        "expected_answer": q["expected_answer"],
        "hint": q["hint"],
        "topic": topic,
        "difficulty": difficulty,
    }


@router.post("/answer/judge")
async def mock_judge_answer(body: dict):
    """Mock: simple string overlap scoring."""
    player_answer = body.get("player_answer", "").lower().strip()
    expected_answer = body.get("expected_answer", "").lower().strip()

    if not player_answer:
        return {
            "score": 0.0,
            "damage_multiplier": 0.0,
            "verdict": "incorrect",
            "feedback": "No answer provided.",
        }

    # Simple word overlap scoring
    player_words = set(player_answer.split())
    expected_words = set(expected_answer.split())

    if not expected_words:
        overlap = 0.0
    else:
        overlap = len(player_words & expected_words) / len(expected_words)

    if overlap >= 0.5:
        verdict = "correct"
        damage_multiplier = 2.0
        feedback = "Great answer! You dealt critical damage!"
    elif overlap >= 0.2:
        verdict = "partial"
        damage_multiplier = 1.0
        feedback = "Partially correct. You dealt some damage."
    else:
        verdict = "incorrect"
        damage_multiplier = 0.0
        feedback = "Incorrect. The enemy strikes back!"

    return {
        "score": round(overlap, 2),
        "damage_multiplier": damage_multiplier,
        "verdict": verdict,
        "feedback": feedback,
    }


@router.post("/difficulty/next")
async def mock_next_difficulty(body: dict):
    """Mock: always returns medium."""
    return {"difficulty": "medium"}


@router.post("/graph/next-topic")
async def mock_next_topic(body: dict):
    """Mock: returns first topic with lowest accuracy."""
    accuracy_history = body.get("accuracy_history", {})

    if not accuracy_history:
        return {"next_topic": "arrays", "weak_topics": ["arrays"]}

    # Find weakest
    weakest = min(accuracy_history, key=lambda t: accuracy_history[t])
    weak_topics = [t for t, a in accuracy_history.items() if a < 0.5]

    return {"next_topic": weakest, "weak_topics": weak_topics or [weakest]}


@router.get("/dashboard/{player_id}")
async def mock_dashboard(player_id: str):
    """Dashboard — aggregates real player data even in mock AI mode."""
    from db.database import SessionLocal
    from models.accuracy_history import AccuracyHistory
    from models.submission import AnswerSubmission
    from models.question import Question
    from services.knowledge_graph import TOPIC_GRAPH

    db = SessionLocal()
    try:
        histories = db.query(AccuracyHistory).filter(
            AccuracyHistory.player_id == player_id
        ).all()

        topic_accuracies = {h.topic: h.recent_accuracy for h in histories}

        # Last 20 submissions with topic names
        submissions = db.query(AnswerSubmission, Question).join(
            Question, AnswerSubmission.question_id == Question.question_id
        ).filter(
            AnswerSubmission.player_id == player_id
        ).order_by(AnswerSubmission.submitted_at.desc()).limit(20).all()

        score_history = [
            {"score": s.score, "verdict": s.verdict, "topic": q.topic,
             "difficulty": q.difficulty, "response_time_ms": s.response_time_ms,
             "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None}
            for s, q in submissions
        ]

        difficulty_history = [
            {"topic": q.topic, "difficulty": q.difficulty}
            for s, q in submissions
        ]

        # Graph state — locked/unlocked/mastered per topic
        graph_state = {}
        for topic, prereqs in TOPIC_GRAPH.items():
            acc = topic_accuracies.get(topic, 0)
            if acc >= 0.9:
                graph_state[topic] = "mastered"
            elif not prereqs:
                graph_state[topic] = "unlocked"
            elif all(topic_accuracies.get(p, 0) > 0.65 for p in prereqs):
                graph_state[topic] = "unlocked"
            else:
                graph_state[topic] = "locked"

        return {
            "player_id": player_id,
            "topic_accuracies": topic_accuracies,
            "score_history": score_history,
            "difficulty_history": difficulty_history,
            "graph_state": graph_state,
        }
    finally:
        db.close()
