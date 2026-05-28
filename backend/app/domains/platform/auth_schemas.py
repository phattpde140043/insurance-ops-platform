from pydantic import BaseModel


class GoogleLoginOut(BaseModel):
    provider: str
    client_id: str
    scope: str
    response_type: str
    next_step: str


class GoogleCallbackIn(BaseModel):
    id_token: str


class GoogleProfileOut(BaseModel):
    provider: str
    subject: str
    email: str
    name: str
    avatar_url: str | None = None


class SessionTokenOut(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class GoogleCallbackOut(BaseModel):
    profile: GoogleProfileOut
    session: SessionTokenOut
    next_step: str
