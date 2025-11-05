from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class CommandType(str, Enum):
    GET_TEMPERATURE_STATS = "GET_TEMPERATURE_STATS"
    GET_SYSTEM_STATUS = "GET_SYSTEM_STATUS"
    PING = "PING"
    GET_ANGLES = "GET_ANGLES"

class CommandRequest(BaseModel):
    type: CommandType = Field(..., description="Tipo do comando")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Dados específicos do comando")
    correlation_id: Optional[str] = Field(None, description="ID para correlacionar resposta no Mendix")

class CommandResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    correlation_id: Optional[str] = None

    
