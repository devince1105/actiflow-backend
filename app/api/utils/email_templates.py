# app/api/utils/email_templates.py

# ============================================================
# Verification Email
# ============================================================
from html import escape


def verification_email_html(verify_url: str) -> str:
    return f"""
    <p>請點擊以下連結完成 Email 驗證：</p>
    <a href="{verify_url}">{verify_url}</a>
    """

# ============================================================
# Submission Approved (Completed) Email
# ============================================================

def submission_completed_email(
    *,
    project_name: str,
    event_name: str,
    submission_code: str,
) -> tuple[str, str]:
    subject = f"【{project_name}】{event_name} 報名已通過"

    body = f"""<p>您好，</p>
<p>您報名的「{escape(event_name)}」已通過主辦單位審核。</p>
<p>報名編號：<strong>{escape(submission_code)}</strong></p>
<p>請登入 ActiFlow 查看活動資訊。</p>"""
    return subject, body


# ============================================================
# Submission Rejected Email
# ============================================================

def submission_rejected_email(
    *,
    project_name: str,
    event_name: str,
    submission_code: str,
    reason: str,
) -> tuple[str, str]:
    subject = f"【{project_name}】{event_name} 報名未通過"
    body = f"""<p>您好，</p>
<p>您報名的「{escape(event_name)}」未能通過審核。</p>
<p>報名編號：<strong>{escape(submission_code)}</strong></p>
<p>原因：{escape(reason)}</p>"""
    return subject, body

# ============================================================
# Submission Reopened Email
# ============================================================

def submission_reopened_email(
    *,
    project_name: str,
    event_name: str,
    submission_code: str,
    note: str,
) -> tuple[str, str]:
    subject = f"【{project_name}】{event_name} 報名已重新開啟"
    body = f"""<p>您好，</p>
<p>「{escape(event_name)}」的報名已重新開啟。</p>
<p>報名編號：<strong>{escape(submission_code)}</strong></p>
<p>說明：{escape(note)}</p>"""
    return subject, body


def submission_email_verified_email(
    *, project_name: str, event_name: str, submission_code: str
) -> tuple[str, str]:
    return (
        f"【{project_name}】{event_name} 報名確認完成",
        f"""<p>您的 Email 已完成驗證。</p>
<p>活動：{escape(event_name)}</p>
<p>報名編號：<strong>{escape(submission_code)}</strong></p>
<p>主辦單位將依活動流程處理您的報名。</p>""",
    )


def submission_canceled_email(
    *, project_name: str, event_name: str, submission_code: str
) -> tuple[str, str]:
    return (
        f"【{project_name}】{event_name} 報名已取消",
        f"""<p>您的活動報名已取消。</p>
<p>活動：{escape(event_name)}</p>
<p>報名編號：<strong>{escape(submission_code)}</strong></p>""",
    )
