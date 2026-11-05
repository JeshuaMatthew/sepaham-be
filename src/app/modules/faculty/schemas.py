from pydantic import BaseModel, ConfigDict, Field

class RoleResponse(BaseModel):
    id: str
    title: str
    emoji: str = ""
    tagline: str = ""
    description: str = ""
    accent: str = ""

    model_config = ConfigDict(populate_by_name=True)


class RoleUpsertRequest(BaseModel):
    title: str = Field(..., min_length=1)
    emoji: str = ""
    tagline: str = ""
    description: str = ""
    accent: str = ""
