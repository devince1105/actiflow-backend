from app.services.submission import notification


def test_rejection_notification_escapes_user_controlled_content(monkeypatch):
    sent = []
    monkeypatch.setattr(
        notification,
        "send_generic_email",
        lambda **kwargs: sent.append(kwargs),
    )

    notification.send_submission_status_email(
        email="participant@example.com",
        event_name="<script>event</script>",
        submission_code="SUB-123",
        target_status="rejected",
        reason="<b>unsafe</b>",
        submission_uuid="submission-id",
    )

    assert sent[0]["to_email"] == "participant@example.com"
    assert "<script>" not in sent[0]["html"]
    assert "&lt;script&gt;" in sent[0]["html"]
    assert "<b>unsafe</b>" not in sent[0]["html"]


def test_notification_failure_does_not_escape(monkeypatch):
    monkeypatch.setattr(
        notification,
        "send_generic_email",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("mailer down")),
    )

    notification.send_submission_status_email(
        email="participant@example.com",
        event_name="測試活動",
        submission_code="SUB-123",
        target_status="completed",
    )
