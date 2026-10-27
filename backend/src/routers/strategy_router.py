from fastapi import APIRouter

from dto.strategy_response import StrategyDefinition
from services.strategy_catalog import get_strategy_catalog


strategies_router = APIRouter(prefix="/strategies", tags=["strategies"])


@strategies_router.get("", response_model=list[StrategyDefinition])
def list_strategies() -> list[StrategyDefinition]:
    """Expose registered defaults and metadata without running strategies."""
    return get_strategy_catalog()
