from typing import List, Optional
from pydantic import BaseModel, Field, AwareDatetime

# ---- entrada do endpoint ----
class InboundRequest(BaseModel):
    Date: AwareDatetime = Field(..., description="UTC ISO8601")
    Side: str = Field(..., pattern="^(LEFT|RIGHT)$")

# ---- resposta do GET ----
class SourceImage(BaseModel):
    Side: str
    Port: int
    Section: int
    IsThermal: bool
    Base64String: str
    Name: str

class SourceCollection(BaseModel):
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

class TemperatureRecord(BaseModel):
    Timestamp: str
    Side: str
    Port: int
    Section: int
    Temperature: float

class ValveRecord(BaseModel):
    Timestamp: str
    Side: str
    Port: int
    Section: int
    Valve_1: Optional[float] = None
    Valve_2: Optional[float] = None
    Valve_3: Optional[float] = None

class MixedResponse(BaseModel):
    temperatures: List[TemperatureRecord]
    valves: List[ValveRecord]
