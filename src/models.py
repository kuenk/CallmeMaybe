from typing import Literal, Any, Optional
from pydantic import BaseModel

class FunctionParameter(BaseModel):
    type: Literal["number", "string", "boolean"]

class FunctionDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, FunctionParameter]
    returns: FunctionParameter | None = None

class TestPrompt(BaseModel):
    prompt: str

class ExitTest(BaseModel):
    prompt: str
    name: str
    parameters: dict[str, Any]