from typing import Literal, Any
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


class FunctionCallResult(BaseModel):
    prompt: str
    name: str
    parameters: dict[str, Any]


class GenerationError(Exception):
    """Raised when the constrained generation process cannot produce a """
    """usable value (invalid grammar state, generation cut short, etc.)"""
