from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field

class RoleItem(BaseModel):
    id: str
    title: str
    emoji: str = ""
    tagline: str = ""
    description: str = ""
    accent: str = ""
    match_tags: list[str] = Field(default_factory=list, serialization_alias="matchTags", validation_alias="matchTags")
    tech_stack: list[str] = Field(default_factory=list, serialization_alias="techStack", validation_alias="techStack")

    model_config = ConfigDict(populate_by_name=True)

class RolesResponse(BaseModel):
    roles: list[RoleItem]

# Catatan: schema pertanyaan Likert lama (`QuestionItem`/`QuestionsResponse`/
# `ReplaceQuestions*`) dihapus bersama endpointnya. Bank soal onboarding kini
# berada di `src.app.modules.onboarding.schemas` dengan bentuk
# `{id, pillar_id, fact_id, question_text, question_type, options, sort_order}`.

class InternshipContactItem(BaseModel):
    id: str
    company: str
    emoji: str = ""
    position: str
    role_id: Optional[str] = Field(default=None, serialization_alias="roleId", validation_alias="roleId")
    location: str = ""
    type: str = ""
    pic: str = ""
    contact: str = ""
    note: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class InternshipsResponse(BaseModel):
    contacts: list[InternshipContactItem]

class DevQuoteItem(BaseModel):
    text: str
    author: str

class AiInternshipItem(BaseModel):
    id: str
    company: str
    emoji: str = ""
    role: str
    location: str = ""
    type: str = ""
    match_percent: int = Field(default=0, serialization_alias="matchPercent", validation_alias="matchPercent")
    tags: list[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

class AiNudgeItem(BaseModel):
    """
    Nudge streak di Home. Semua field diisi server dari `github_stats` milik user
    — jangan pernah mengembalikan angka hardcoded di sini, karena Home akan
    menampilkan streak yang sama untuk semua akun.
    """
    title: str = "Keep your streak alive!"
    message: str = "Hubungkan GitHub untuk mulai menghitung streak commit-mu."
    streak: int = 0
    # `cta` kosong = jangan render link CTA. Dipakai saat kartu hanya
    # informatif (belum ada data GitHub), supaya tidak mengarah ke halaman
    # yang tidak offers cara menghubungkan akun.
    cta: str = "Open GitHub"

class AiFeedResponse(BaseModel):
    quotes: list[DevQuoteItem]
    nudge: AiNudgeItem = Field(default_factory=AiNudgeItem)
    internships: list[AiInternshipItem]

class LofiTrackItem(BaseModel):
    id: str
    title: str
    artist: str

class LofiTracksResponse(BaseModel):
    tracks: list[LofiTrackItem]

class UserPreferenceResponse(BaseModel):
    role_id: Optional[str] = Field(default=None, serialization_alias="roleId", validation_alias="roleId")
    role_title: str = Field(default="", serialization_alias="roleTitle", validation_alias="roleTitle")
    role_emoji: str = Field(default="", serialization_alias="roleEmoji", validation_alias="roleEmoji")
    role_scores: dict[str, Any] = Field(default_factory=dict, serialization_alias="roleScores", validation_alias="roleScores")

    model_config = ConfigDict(populate_by_name=True)

class UserPreferenceUpdateRequest(BaseModel):
    role_id: Optional[str] = Field(default=None, alias="roleId")
    role_title: str = Field(default="", alias="roleTitle")
    role_emoji: str = Field(default="", alias="roleEmoji")
    role_scores: dict[str, Any] = Field(default_factory=dict, alias="roleScores")

    model_config = ConfigDict(populate_by_name=True)
