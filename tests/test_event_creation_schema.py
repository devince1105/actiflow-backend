from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.event.organizer.event_create import OrganizerEventCreate


def _payload():
    start = datetime(2026, 9, 20, 9, 0)
    return {
        "name": "城市健行活動",
        "description": "一起探索城市步道。",
        "event_category_uuid": uuid4(),
        "location": "台北車站東三門",
        "max_capacity": 80,
        "start_date": start,
        "end_date": start + timedelta(hours=4),
        "registration_deadline": start - timedelta(days=1),
    }


def test_event_create_accepts_required_details():
    event = OrganizerEventCreate.model_validate(_payload())

    assert event.max_capacity == 80
    assert event.event_category_uuid


@pytest.mark.parametrize(
    "changes",
    [
        {"event_category_uuid": None},
        {"max_capacity": 0},
        {
            "end_date": datetime(2026, 9, 20, 8, 0),
        },
        {
            "registration_deadline": datetime(2026, 9, 20, 10, 0),
        },
    ],
)
def test_event_create_rejects_invalid_required_details(changes):
    payload = {**_payload(), **changes}

    with pytest.raises(ValidationError):
        OrganizerEventCreate.model_validate(payload)
