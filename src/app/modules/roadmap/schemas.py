from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field

class RoadmapListItem(BaseModel):
    id: str
    role_id: Optional[str] = Field(default=None, serialization_alias="roleId", validation_alias="roleId")
    title: str
    emoji: str = ""
    color: str = ""
    description: str = ""
    difficulty: str = "Beginner"
    match_tags: list[str] = Field(default_factory=list, serialization_alias="matchTags", validation_alias="matchTags")
    author: str = ""
    total_nodes: int = Field(default=0, serialization_alias="totalNodes", validation_alias="totalNodes")

    model_config = ConfigDict(populate_by_name=True)

class RoadmapsListResponse(BaseModel):
    roadmaps: list[RoadmapListItem]

class NodeItem(BaseModel):
    id: str
    title: str
    emoji: str = ""
    x: float = 0.0
    y: float = 0.0
    group: Optional[str] = None
    image: Optional[str] = None
    title_inside: bool = Field(default=False, serialization_alias="titleInside", validation_alias="titleInside")
    always_unlocked: bool = Field(default=False, serialization_alias="alwaysUnlocked", validation_alias="alwaysUnlocked")
    optional: bool = False
    article: Optional[str] = None
    submission: Optional[Any] = None
    resources: Optional[Any] = None
    missions: Optional[Any] = None

    model_config = ConfigDict(populate_by_name=True)

class EdgeItem(BaseModel):
    id: str
    source: str
    target: str
    dashed: bool = False
    optional: bool = False
    animated: bool = False

    model_config = ConfigDict(populate_by_name=True)

class RoadmapDetailResponse(BaseModel):
    id: str
    role_id: Optional[str] = Field(default=None, serialization_alias="roleId", validation_alias="roleId")
    title: str
    emoji: str = ""
    author: str = ""
    style: dict[str, Any] = Field(default_factory=dict)
    nodes: list[NodeItem] = Field(default_factory=list)
    edges: list[EdgeItem] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

class RoadmapUpsertRequest(BaseModel):
    role_id: Optional[str] = Field(default=None, alias="roleId")
    title: Optional[str] = None
    emoji: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[str] = None
    match_tags: Optional[list[str]] = Field(default=None, alias="matchTags")
    author: Optional[str] = None
    style: Optional[dict[str, Any]] = None
    nodes: Optional[list[NodeItem]] = None
    edges: Optional[list[EdgeItem]] = None

    model_config = ConfigDict(populate_by_name=True)

class SubmissionState(BaseModel):
    done: bool = False
    file_name: Optional[str] = Field(default=None, serialization_alias="fileName", validation_alias="fileName")
    text: Optional[str] = None
    score: Optional[int] = None
    quiz_answers: Optional[Any] = Field(default=None, serialization_alias="quizAnswers", validation_alias="quizAnswers")

    model_config = ConfigDict(populate_by_name=True)

class SubmissionUpsertRequest(BaseModel):
    done: Optional[bool] = False
    file_name: Optional[str] = Field(default=None, alias="fileName")
    text: Optional[str] = None
    score: Optional[int] = None
    quiz_answers: Optional[Any] = Field(default=None, alias="quizAnswers")

    model_config = ConfigDict(populate_by_name=True)
