# app/schemas/auth/register_response.py

from pydantic import BaseModel


class RegisterResponse(BaseModel):
    status: str
    email: str
