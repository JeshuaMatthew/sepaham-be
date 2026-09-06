from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class GithubStatsObj(BaseModel):
    total_commits: int = Field(default=0, serialization_alias="totalCommits", validation_alias="totalCommits")
    current_streak: int = Field(default=0, serialization_alias="currentStreak", validation_alias="currentStreak")
    longest_streak: int = Field(default=0, serialization_alias="longestStreak", validation_alias="longestStreak")
    public_repos: int = Field(default=0, serialization_alias="publicRepos", validation_alias="publicRepos")

    model_config = ConfigDict(populate_by_name=True)

class TopLanguageItem(BaseModel):
    name: str
    percentage: int
    color: str

class TopRepoItem(BaseModel):
    id: str
    name: str
    description: str = ""
    stars: int = 0
    forks: int = 0
    language: str = ""
    language_color: str = Field(default="", serialization_alias="languageColor", validation_alias="languageColor")
    url: str = ""

    model_config = ConfigDict(populate_by_name=True)

class GithubCardResponse(BaseModel):
    username: str
    stats: GithubStatsObj
    top_languages: list[TopLanguageItem] = Field(default_factory=list, serialization_alias="topLanguages", validation_alias="topLanguages")
    weeks: list[list[int]] = Field(default_factory=list)
    top_repos: list[TopRepoItem] = Field(default_factory=list, serialization_alias="topRepos", validation_alias="topRepos")

    model_config = ConfigDict(populate_by_name=True)

class GithubConnectRequest(BaseModel):
    username: Optional[str] = "yourhandle"
