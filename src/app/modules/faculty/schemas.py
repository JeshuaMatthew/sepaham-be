from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from src.app.modules.collab.schemas import CollabRequestItem
from src.app.modules.community.schemas import ServerObj

class StudentRoadmap(BaseModel):
    title: str = ""
    completed: int = 0
    total: int = 0

class StudentGithub(BaseModel):
    repos: int = 0
    commits: int = 0
    top_languages: list[str] = Field(default_factory=list, serialization_alias="topLanguages", validation_alias="topLanguages")

    model_config = ConfigDict(populate_by_name=True)

class FacultyStudentItem(BaseModel):
    id: str
    name: str
    avatar: str = ""
    role: str = ""
    cv_file_name: Optional[str] = Field(default=None, serialization_alias="cvFileName", validation_alias="cvFileName")
    cv_uploaded_at: Optional[str] = Field(default=None, serialization_alias="cvUploadedAt", validation_alias="cvUploadedAt")
    roadmap: StudentRoadmap
    github: StudentGithub
    projects: int = 0

    model_config = ConfigDict(populate_by_name=True)

class FacultyStudentsResponse(BaseModel):
    students: list[FacultyStudentItem]

class FacultyServersResponse(BaseModel):
    servers: list[ServerObj]
    banned_ids: list[str] = Field(default_factory=list, serialization_alias="bannedIds", validation_alias="bannedIds")

    model_config = ConfigDict(populate_by_name=True)

class BanServerResponse(BaseModel):
    id: str
    banned: bool

class FacultyRequestsResponse(BaseModel):
    requests: list[CollabRequestItem]
    closed_ids: list[str] = Field(default_factory=list, serialization_alias="closedIds", validation_alias="closedIds")

    model_config = ConfigDict(populate_by_name=True)

class CloseCollabRequestResponse(BaseModel):
    id: str
    closed: bool

