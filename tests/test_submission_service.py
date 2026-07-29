from uuid import uuid4
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.core.exceptions import ActiFlowBusinessException
from app.crud.submission.crud_submission_status import assert_status_transition
from app.services.submission.submission_service import SubmissionService


class _Result:
    def __init__(self, rowcount: int):
        self.rowcount = rowcount


class _FakeDb:
    def __init__(self, rowcount: int = 1):
        self.rowcount = rowcount
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)
        return _Result(self.rowcount)


def test_reopen_requires_an_available_capacity_slot():
    db = _FakeDb(rowcount=0)

    with pytest.raises(ActiFlowBusinessException) as exc:
        SubmissionService._adjust_capacity_for_transition(
            db, uuid4(), "canceled", "pending"
        )

    assert exc.value.code == "EVENT_FULL"


def test_cancel_releases_capacity():
    db = _FakeDb()

    SubmissionService._adjust_capacity_for_transition(
        db, uuid4(), "pending", "canceled"
    )

    assert len(db.statements) == 1


def test_rejected_submission_can_be_reopened():
    assert_status_transition(current="rejected", target="pending")


def test_naive_registration_deadline_does_not_raise_type_error():
    event = SimpleNamespace(
        status="published",
        current_attendance=0,
        max_capacity=10,
        registration_deadline=datetime.now() - timedelta(minutes=1),
    )

    assert SubmissionService.can_register(event) is False
