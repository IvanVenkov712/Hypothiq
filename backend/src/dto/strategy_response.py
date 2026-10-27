from typing import Literal

from pydantic import BaseModel, Field


class ParameterDefinition(BaseModel):
    name: str
    label: str
    description: str = ""
    type: Literal["integer", "number", "boolean", "string"]
    default: bool | int | float | str | None
    nullable: bool = False
    choices: list[str] | None = Field(
        default=None,
        description="Suggested form choices; the execution API may accept other values.",
    )
    minimum: float | None = None
    maximum: float | None = None
    exclusive_minimum: float | None = None
    exclusive_maximum: float | None = None


class StrategyDefinition(BaseModel):
    name: str
    description: str
    parameters: list[ParameterDefinition]
