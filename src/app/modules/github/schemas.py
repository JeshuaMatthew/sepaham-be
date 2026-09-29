from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class GithubStatsObj(BaseModel):
    # Ketiganya nullable dengan sengaja. API publik GitHub tidak menyediakan
    # jumlah commit maupun streak harian tanpa token OAuth, jadi `null` berarti
    # "tidak diketahui". `0` akan berarti "tidak ada commit sama sekali", dan
    # itu klaim yang berbeda.
    total_commits: Optional[int] = Field(
        default=None, serialization_alias="totalCommits", validation_alias="totalCommits"
    )
    current_streak: Optional[int] = Field(
        default=None, serialization_alias="currentStreak", validation_alias="currentStreak"
    )
    longest_streak: Optional[int] = Field(
        default=None, serialization_alias="longestStreak", validation_alias="longestStreak"
    )
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
    # Kosong berarti grafik kontribusi tidak tersedia. Server tidak pernah
    # mengisi dataweeks palsu; lihat `github/service.py`.
    weeks: list[list[int]] = Field(default_factory=list)
    top_repos: list[TopRepoItem] = Field(default_factory=list, serialization_alias="topRepos", validation_alias="topRepos")

    model_config = ConfigDict(populate_by_name=True)

class GithubConnectRequest(BaseModel):
    # Tidak ada default lagi. `"yourhandle"` dulu jadi nilai sentinel yang
    # membuat server melewati pengambilan GitHub dan menyimpan data demo.
    # Wajib diisi eksplisit supaya tidak ada jalur yang bisa mengembalikan
    # angka karangan.
    username: str
