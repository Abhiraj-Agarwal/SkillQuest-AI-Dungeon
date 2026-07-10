"""
Seed script — populates the database with a demo DSA dungeon.
"""
from datetime import datetime, timezone, timedelta
from db.database import SessionLocal
from models.dungeon import Dungeon, Room
from models.player import Player
from models.accuracy_history import AccuracyHistory
from models.submission import AnswerSubmission
from models.question import Question
from services.knowledge_graph import TOPIC_GRAPH


def seed_database():
    """Create the demo DSA dungeon with rooms based on the knowledge graph."""
    db = SessionLocal()

    # Check if already seeded
    existing = db.query(Dungeon).filter(Dungeon.name == "DSA Fundamentals").first()
    if existing:
        boss = db.query(Room).filter(
            Room.dungeon_id == existing.dungeon_id, Room.topic == "boss"
        ).first()
        if not boss:
            for room in existing.rooms:
                room.is_boss = False
            db.add(
                Room(
                    dungeon_id=existing.dungeon_id,
                    topic="boss",
                    enemy_count=5,
                    is_boss=True,
                    is_unlocked=False,
                    order_index=len(existing.rooms),
                )
            )
            db.commit()
            print("Migrated dungeon to a dedicated boss room.")
        print("Database already seeded.")
        db.close()
        return existing.dungeon_id

    # Create dungeon
    dungeon = Dungeon(name="DSA Fundamentals", domain="Data Structures & Algorithms")
    db.add(dungeon)
    db.flush()

    # Create rooms in topological order
    topics_order = list(TOPIC_GRAPH.keys())
    for i, topic in enumerate(topics_order):
        room = Room(
            dungeon_id=dungeon.dungeon_id,
            topic=topic,
            enemy_count=3,
            is_boss=False,
            is_unlocked=(i == 0),  # Only first room starts unlocked
            order_index=i,
        )
        db.add(room)

    db.add(
        Room(
            dungeon_id=dungeon.dungeon_id,
            topic="boss",
            enemy_count=5,
            is_boss=True,
            is_unlocked=False,
            order_index=len(topics_order),
        )
    )

    # Create demo player with pre-populated history
    demo_player = Player(
        username="HeroOfDSA",
        level=5,
        total_xp=450,
        streak_days=7,
        last_active=datetime.now(timezone.utc) - timedelta(hours=12),
        hint_tokens=4,
    )
    db.add(demo_player)
    db.flush()

    # Pre-populate accuracy history for first 5 topics
    demo_topics = {
        "arrays": (10, 8, 0.8),         # 10 attempts, 8 correct, 80% accuracy
        "linked_lists": (8, 6, 0.75),
        "stacks_queues": (6, 4, 0.67),
        "binary_search": (5, 3, 0.6),
        "recursion": (4, 2, 0.5),
    }
    for topic, (attempts, correct, accuracy) in demo_topics.items():
        history = AccuracyHistory(
            player_id=demo_player.player_id,
            topic=topic,
            attempts=attempts,
            correct=correct,
            recent_accuracy=accuracy,
            last_5_results=[True] * correct + [False] * (min(5, attempts) - correct),
        )
        db.add(history)

    db.commit()
    print(f"Seeded dungeon: {dungeon.name} (ID: {dungeon.dungeon_id})")
    print(f"Created {len(topics_order)} topic rooms and one boss room.")
    print(f"Created demo player: {demo_player.username} (ID: {demo_player.player_id})")

    dungeon_id = dungeon.dungeon_id
    db.close()
    return dungeon_id


if __name__ == "__main__":
    seed_database()
