from typing import Optional
from pydantic import BaseModel


class AiAssistRequest(BaseModel):
    message: str
    intent: Optional[str] = "career_path"


class AiAssistResponse(BaseModel):
    response: str
    # Asal jawaban: "llm" kalau benar-benar memanggil model, "rule_based" kalau
    # jatuh ke template. Tanpa ini frontend tidak bisa jujur soal apa yang
    # terjadi — sebelumnya keduanya terlihat sama persis dari sisi klien.
    source: str = "rule_based"


class AiGenerateRequest(BaseModel):
    message: str


class AiGenerateResponse(BaseModel):
    response: str
    source: str = "rule_based"
