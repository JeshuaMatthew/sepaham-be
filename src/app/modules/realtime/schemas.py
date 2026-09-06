from pydantic import BaseModel

class CallTokenRequest(BaseModel):
    room: str

class CallTokenResponse(BaseModel):
    token: str
    url: str
    identity: str
    name: str
    room: str

