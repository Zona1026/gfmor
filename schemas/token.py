from pydantic import BaseModel
from schemas.user import User

class GoogleToken(BaseModel):
    token: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

class LoginResponse(Token):
    user: User
