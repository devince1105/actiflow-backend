from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core.rate_limit import check_rate_limit_per_ip
from app.main import app


def test_public_api_does_not_expose_mark_paid_mutation():
    public_methods_by_path = {
        route.path: route.methods
        for route in app.routes
        if hasattr(route, "methods")
    }

    assert (
        "/public/events/submissions/{submission_uuid}/mark-paid"
        not in public_methods_by_path
    )


def test_registration_rate_limit_is_scoped_by_event_and_ip():
    event_uuid = uuid4()
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": [],
            "client": ("203.0.113.10", 12345),
        }
    )

    check_rate_limit_per_ip(request, event_uuid, limit=2)
    check_rate_limit_per_ip(request, event_uuid, limit=2)

    with pytest.raises(HTTPException) as exc:
        check_rate_limit_per_ip(request, event_uuid, limit=2)

    assert exc.value.status_code == 429
    assert exc.value.detail["code"] == "RATE_LIMIT_EXCEEDED"

    # A different event must have its own allowance.
    check_rate_limit_per_ip(request, uuid4(), limit=2)
