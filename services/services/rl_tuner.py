"""
RL Difficulty Tuner (P3-owned, README section 4.3).

Pure sync logic, no API calls.
"""

import random

import config

_DIFFICULTIES = ("easy", "medium", "hard")


def _greedy_difficulty(recent_accuracy: float) -> str:
    """Threshold-based difficulty pick, ignoring exploration."""
    if recent_accuracy > config.RL_HARD_THRESHOLD:
        return "hard"
    elif recent_accuracy > config.RL_MEDIUM_THRESHOLD:
        return "medium"
    return "easy"


# INTEGRATION POINT: accuracy_history is sent by Person 2 in the request
# body. Person 2 builds it from their AccuracyHistory DB table, updated on
# every POST /game/answer/submit. For local testing, use mocks/mock_data.py.
def get_next_difficulty(player_id: str, topic: str, accuracy_history: dict) -> dict:
    """
    Decide the difficulty for a player's next question on a given topic.

    Inputs:
        player_id: str -- accepted to match the README's request contract;
            not used by the bandit logic itself (the bandit is stateless
            per-call and only reads accuracy_history.recent_accuracy).
        topic: str -- topic the player is about to fight in.
        accuracy_history: dict -- README schema, keyed by topic name. See
            mocks/mock_data.py for examples.

    Output:
        dict matching the POST /ai/difficulty/next response contract, plus
        an internal "_reason" field for the ML dashboard:
        { difficulty, _reason }

    P2 dependency: accuracy_history must come from Person 2's DB in
    production (see INTEGRATION POINT above). Fully testable solo with
    mocked accuracy_history dicts.

    DECISION (locked with user): epsilon-greedy is implemented per the
    textbook definition -- with probability RL_EPSILON, return a uniformly
    random difficulty from all three options (which may coincidentally
    match the greedy choice); otherwise return the threshold-based greedy
    choice.
    """
    if topic not in accuracy_history:
        # INTEGRATION NOTE: handles brand new players before Person 2 has
        # written any accuracy data for this topic.
        return {
            "difficulty": "easy",
            "_reason": "no accuracy_history entry for this topic yet -- defaulting to easy",
        }

    recent_accuracy = accuracy_history[topic]["recent_accuracy"]
    greedy_choice = _greedy_difficulty(recent_accuracy)

    if random.random() < config.RL_EPSILON:
        explore_choice = random.choice(_DIFFICULTIES)
        return {
            "difficulty": explore_choice,
            "_reason": (
                f"exploration (epsilon={config.RL_EPSILON}): random pick "
                f"'{explore_choice}' overriding greedy choice '{greedy_choice}'"
            ),
        }

    return {
        "difficulty": greedy_choice,
        "_reason": f"greedy: recent_accuracy={recent_accuracy} -> '{greedy_choice}'",
    }
