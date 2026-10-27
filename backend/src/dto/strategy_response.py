from typing import Literal

from pydantic import BaseModel, Field


class ParameterDefinition(BaseModel):
    """Form metadata whose suggestions and bounds do not add execution rules."""

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
    """Separate the executable class_name from its human-readable display name."""

    class_name: str = Field(description="Registry identifier to submit as strategy.name in a backtest request.")
    name: str = Field(description="Human-readable strategy name for display.")
    description: str
    parameters: list[ParameterDefinition]
