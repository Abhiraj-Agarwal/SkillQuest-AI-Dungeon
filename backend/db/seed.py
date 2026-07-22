"""
Seed script — populates the database with a demo DSA dungeon.
"""
import random
from datetime import datetime, timezone, timedelta
from db.database import SessionLocal
from models.dungeon import Dungeon, Room
from models.player import Player
from models.accuracy_history import AccuracyHistory
from models.submission import AnswerSubmission
from models.question import Question
from services.knowledge_graph import TOPIC_GRAPH

# Each topic boss gets a randomized HP pool in this band rather than a flat
# "3 hits always clears it" -- deliberately not tied to knowledge-graph depth
# (a later/deeper topic isn't guaranteed a bigger pool than an earlier one),
# so bosses genuinely differ in how much of a fight they put up. The final
# boss's pool is drawn from its own, dramatically larger band -- meant to
# read as unequaled next to every topic boss.
TOPIC_HP_RANGE = (140, 320)
BOSS_HP_RANGE = (900, 1400)


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
                    enemy_count=random.randint(*BOSS_HP_RANGE),
                    is_boss=True,
                    is_unlocked=False,
                    order_index=len(existing.rooms),
                )
            )
            db.commit()
            print("Migrated dungeon to a dedicated boss room.")

        # One-time backfill: rooms created before boss HP was randomized all
        # share the same flat enemy_count=3 (topics) / 5 (boss) placeholder
        # from the old "3 correct answers always clears it" design -- an
        # existing dev database wouldn't otherwise ever pick up varied HP.
        stale_rooms = db.query(Room).filter(
            Room.dungeon_id == existing.dungeon_id,
            Room.enemy_count.in_([3, 5]),
        ).all()
        if stale_rooms:
            for room in stale_rooms:
                room.enemy_count = random.randint(*BOSS_HP_RANGE) if room.is_boss else random.randint(*TOPIC_HP_RANGE)
            db.commit()
            print(f"Backfilled varied boss HP onto {len(stale_rooms)} room(s).")

        # One-time backfill: AccuracyHistory rows written before damage_dealt
        # existed have no record of it (defaults to 0), even for topics a
        # player actually cleared under the old "N correct answers" model.
        # Without this, every pre-existing "cleared" room would regress to
        # 0% complete and, for any topic that hadn't also crossed the 65%
        # mastered/accuracy ratchet on its own, silently re-lock everything
        # downstream of it. correct >= 3 (topics) / >= 5 (boss) was the exact
        # old universal clear threshold, so it's used here (not `mastered` or
        # `recent_accuracy`, which are a different, already-independent proof
        # path and would falsely mark a barely-started-but-mastered topic as
        # fully cleared).
        rooms_by_topic = {room.topic: room for room in existing.rooms}
        histories = db.query(AccuracyHistory).all()
        backfilled = 0
        for history in histories:
            if history.damage_dealt:
                continue
            room = rooms_by_topic.get(history.topic)
            if not room:
                continue
            old_clear_threshold = 5 if room.is_boss else 3
            if (history.correct or 0) >= old_clear_threshold:
                history.damage_dealt = room.enemy_count
                backfilled += 1
        if backfilled:
            db.commit()
            print(f"Backfilled damage_dealt for {backfilled} previously-cleared room(s).")
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
            enemy_count=random.randint(*TOPIC_HP_RANGE),
            is_boss=False,
            is_unlocked=(i == 0),  # Only first room starts unlocked
            order_index=i,
        )
        db.add(room)

    db.add(
        Room(
            dungeon_id=dungeon.dungeon_id,
            topic="boss",
            enemy_count=random.randint(*BOSS_HP_RANGE),
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
