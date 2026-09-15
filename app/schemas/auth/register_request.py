# app/schemas/auth/register_request.py

from pydantic import BaseModel, EmailStr, Field
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=100)
