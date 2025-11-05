from typing import List, Optional
from pydantic import BaseModel, Field, AwareDatetime

# ---- entrada do endpoint ----
class InboundRequest(BaseModel):
    Date: AwareDatetime = Field(..., description="UTC ISO8601")
    Side: str = Field(..., pattern="^(LEFT|RIGHT)$")
    Equipment: Optional[str] = Field(None, description="Opcional - identifica o equipamento")

# ---- resposta do GET ----
class SourceImage(BaseModel):
    Side: str
    Port: int
    Section: int
    IsThermal: bool
    Name: str
    Base64String: str

class SourceResponse(BaseModel):
    Side: str
    Date: AwareDatetime
    Images: List[SourceImage]

class StoredImage(BaseModel):
    Side: str
    Port: int
    Section: int
    IsThermal: bool
    Name: str
    temperatures: List[float] = Field(default_factory=list)
    length: int = 0

class AggregatedPayload(BaseModel):
    Side: str
    Date: AwareDatetime
    Images: List[StoredImage]
