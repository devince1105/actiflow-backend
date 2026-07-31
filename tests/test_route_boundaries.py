from uuid import uuid4
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.main import app
from app.api.organizers.organizer.detail import get_current_organizer
from app.api.organizers.organizer.submissions import (
    BulkActionRequest,
    bulk_action_submissions,
)
from app.core.exceptions import ActiFlowBusinessException, ActiFlowErrorCode
from app.services.submission.submission_service import SubmissionService


class _Query:
    def __init__(self, result):
        self.result = result
        self.filters = []

    def filter(self, *conditions):
        self.filters.extend(conditions)
        return self

    def first(self):
        return self.result


class _Db:
    def __init__(self, result):
        self.query_result = _Query(result)

    def query(self, _model):
        return self.query_result


def _methods_by_path() -> dict[str, set[str]]:
    return {
        route.path: route.methods
        for route in app.routes
        if hasattr(route, "methods")
    }


def test_canonical_organizer_detail_route_is_mounted():
    methods = _methods_by_path()

    assert methods["/organizers/{organizer_uuid}"] == {"GET"}


def test_legacy_organizer_crud_is_not_mounted_under_public_prefix():
    methods = _methods_by_path()

    assert "/public/organizers/organizers/" not in methods
    assert "/public/organizers/organizers/{organizer_uuid}" not in methods


def test_canonical_organizer_detail_queries_the_path_organizer():
    organizer_uuid = uuid4()
    organizer = object()
    db = _Db(organizer)

    result = get_current_organizer(
        organizer_uuid=organizer_uuid,
        db=db,
        _membership=object(),
    )

    assert result is organizer
    filters = " ".join(str(condition) for condition in db.query_result.filters)
    assert "organizers.uuid" in filters
    assert "organizers.is_deleted" in filters


def test_bulk_action_rejects_event_outside_path_organizer():
    with pytest.raises(HTTPException) as exc:
        bulk_action_submissions(
            event_uuid=uuid4(),
            req=BulkActionRequest(action="approve", submission_uuids=[]),
            background_tasks=BackgroundTasks(),
            db=_Db(None),
            membership=SimpleNamespace(
                organizer_uuid=uuid4(),
                user_uuid=uuid4(),
            ),
        )

    assert exc.value.status_code == 404


def test_bulk_action_uses_business_error_for_invalid_action():
    with pytest.raises(ActiFlowBusinessException) as exc:
        SubmissionService.bulk_action(
            db=object(),
            event_uuid=uuid4(),
            submission_uuids=[],
            action="invalid",
            actor_id=uuid4(),
            actor_role="organizer",
        )

    assert exc.value.code == ActiFlowErrorCode.INVALID_STATUS
