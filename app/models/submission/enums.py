# app/models/submission/enums.py

import enum

class SubmissionStatus(str, enum.Enum):
    pending = "pending"
    email_verified = "email_verified"
    paid = "paid"
    canceled = "canceled"
    completed = "completed"
    waitlist = "waitlist"
    expired = "expired"
    rejected = "rejected"

