"""Seed long-lived upcoming demo events.

Preview:
    venv/bin/python scripts/seed_upcoming_events.py

Write to the configured database:
    venv/bin/python scripts/seed_upcoming_events.py --apply
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.constants.event_status import EventStatus
from app.core.db import SessionLocal
from app.models.event.event import Event
from app.models.event.event_category import EventCategory
from app.models.event.event_media import EventMedia
from app.models.organizer.organizer import Organizer


EVENTS = [
    {
        "code": "demo-future-hiking",
        "name": "秋季森林健行日",
        "description": "適合初學者的森林步道健行，一起享受秋日山林。",
        "days": 45,
        "duration_hours": 6,
        "location": "陽明山國家公園",
        "capacity": 80,
        "category": "SPORTS_OUTDOOR",
        "organizer": "Taiwan Hiking Association",
    },
    {
        "code": "demo-future-photo",
        "name": "城市夜景攝影工作坊",
        "description": "從構圖到長曝光，實地練習城市夜景拍攝技巧。",
        "days": 90,
        "duration_hours": 4,
        "location": "台北信義區",
        "capacity": 30,
        "category": "PHOTOGRAPHY_MEDIA",
        "organizer": "City Photography Society",
    },
    {
        "code": "demo-future-charity",
        "name": "河岸淨灘志工行動",
        "description": "一起整理河岸環境，活動提供工具與志工服務證明。",
        "days": 150,
        "duration_hours": 4,
        "location": "淡水河岸",
        "capacity": 120,
        "category": "CHARITY_VOLUNTEER",
        "organizer": "Nature Conservation Alliance",
    },
    {
        "code": "demo-future-running",
        "name": "城市晨光路跑",
        "description": "5 公里與 10 公里雙組別，適合各程度跑者參加。",
        "days": 210,
        "duration_hours": 5,
        "location": "大佳河濱公園",
        "capacity": 300,
        "category": "SPORTS_OUTDOOR",
        "organizer": "Urban Runners Club",
    },
    {
        "code": "demo-future-creative",
        "name": "週末手作創意市集",
        "description": "集合插畫、陶藝與生活選物的週末創意活動。",
        "days": 270,
        "duration_hours": 8,
        "location": "華山1914文化創意產業園區",
        "capacity": 500,
        "category": "ARTS_CREATIVE",
        "organizer": "Test Organizer",
    },
    {
        "code": "demo-future-workshop",
        "name": "AI 生產力實戰工作坊",
        "description": "透過實作學習如何把 AI 工具導入日常工作流程。",
        "days": 330,
        "duration_hours": 7,
        "location": "台北市數位學習中心",
        "capacity": 60,
        "category": "WORKSHOPS_LEARNING",
        "organizer": "Test Organizer",
    },
    {
        "code": "demo-future-family",
        "name": "親子自然探索日",
        "description": "由生態老師帶領親子觀察植物、昆蟲與自然環境。",
        "days": 420,
        "duration_hours": 6,
        "location": "關渡自然公園",
        "capacity": 100,
        "category": "FAMILY_KIDS",
        "organizer": "Nature Conservation Alliance",
    },
    {
        "code": "demo-future-community",
        "name": "城市社群年度交流會",
        "description": "跨領域社群分享、交流與合作媒合活動。",
        "days": 540,
        "duration_hours": 8,
        "location": "台北國際會議中心",
        "capacity": 400,
        "category": "COMMUNITY_MEETUP",
        "organizer": "Test Organizer",
    },
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes. Without this flag, only show a preview.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        now = datetime.now().replace(second=0, microsecond=0)
        existing_codes = {
            code
            for (code,) in db.query(Event.event_code)
            .filter(Event.event_code.in_([item["code"] for item in EVENTS]))
            .all()
        }
        categories = {
            category.code: category
            for category in db.query(EventCategory)
            .filter(
                EventCategory.code.in_([item["category"] for item in EVENTS]),
                EventCategory.is_deleted == False,
            )
            .all()
        }
        organizers = {
            organizer.name: organizer
            for organizer in db.query(Organizer)
            .filter(
                Organizer.name.in_([item["organizer"] for item in EVENTS]),
                Organizer.is_deleted == False,
            )
            .all()
        }

        created = 0
        skipped = 0
        for index, item in enumerate(EVENTS, start=1):
            if item["code"] in existing_codes:
                print(f"SKIP   {item['code']} (already exists)")
                skipped += 1
                continue

            category = categories.get(item["category"])
            organizer = organizers.get(item["organizer"])
            if not category or not organizer:
                raise RuntimeError(
                    f"Missing category or organizer for {item['code']}"
                )

            start_date = (now + timedelta(days=item["days"])).replace(
                hour=9 if index % 2 else 14,
                minute=0,
            )
            end_date = start_date + timedelta(hours=item["duration_hours"])
            registration_deadline = start_date - timedelta(days=7)
            print(
                f"{'CREATE' if args.apply else 'PREVIEW'} "
                f"{item['code']} | {start_date:%Y-%m-%d %H:%M} | {item['name']}"
            )

            if not args.apply:
                continue

            event = Event(
                event_code=item["code"],
                slug=item["code"],
                status=EventStatus.PUBLISHED,
                max_capacity=item["capacity"],
                current_attendance=0,
                event_category_uuid=category.uuid,
                organizer_uuid=organizer.uuid,
                name=item["name"],
                description=item["description"],
                content={},
                start_date=start_date,
                end_date=end_date,
                registration_deadline=registration_deadline,
                location=item["location"],
                config={"seed": "upcoming-demo-v1"},
                is_active=True,
                is_deleted=False,
            )
            event.media.append(
                EventMedia(
                    media_type="image",
                    url=f"https://picsum.photos/seed/{item['code']}/1200/800",
                    title=f"{item['name']}封面",
                    sort_order=0,
                    is_cover=True,
                    config={"seed": "upcoming-demo-v1"},
                )
            )
            db.add(event)
            created += 1

        if args.apply:
            db.commit()
            print(f"DONE   created={created} skipped={skipped}")
        else:
            print(f"DRY RUN   pending={len(EVENTS) - skipped} skipped={skipped}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
