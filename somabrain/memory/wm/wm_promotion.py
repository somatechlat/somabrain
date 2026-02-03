"""Working Memory to Long-Term Memory Promotion Module.

This module provides WM→LTM promotion logic for the WorkingMemory class.
Items with sustained high salience are promoted to long-term memory.

Extracted from wm.py to maintain <500 line file size per VIBE Coding Rules.

Key Functions:
    check_promotion: Check if an item should be promoted to LTM
    schedule_promotion_check: Schedule async promotion check without blocking

Per Requirement A2.1: Items with salience >= 0.85 for 3+ consecutive
ticks are promoted to LTM.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from somabrain.memory.promotion import WMLTMPromoter
    from somabrain.memory.wm.core import WMItem

logger = logging.getLogger(__name__)


def check_promotion(
    promoter: "WMLTMPromoter",
    item_id: str,
    salience: float,
    tick: int,
    item: "WMItem",
) -> None:
    """Check if item should be promoted to LTM.

    Per Requirement A2.1: Items with salience >= 0.85 for 3+ consecutive
    ticks are promoted to LTM.

    This function schedules an async promotion check without blocking
    the calling code.

    Args:
        promoter: WMLTMPromoter instance for handling promotions.
        item_id: Unique identifier for the WM item.
        salience: Current salience score (0.0-1.0).
        tick: Current tick count.
        item: The WMItem to potentially promote.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(
                promoter.check_and_promote(
                    item_id=item_id,
                    salience=salience,
                    tick=tick,
                    vector=item.vector.tolist(),
                    payload=item.payload,
                )
            )
        else:
            # No running loop - run synchronously
            loop.run_until_complete(
                promoter.check_and_promote(
                    item_id=item_id,
                    salience=salience,
                    tick=tick,
                    vector=item.vector.tolist(),
                    payload=item.payload,
                )
            )
    except RuntimeError:
        # No event loop available - try asyncio.run
        try:
            asyncio.run(
                promoter.check_and_promote(
                    item_id=item_id,
                    salience=salience,
                    tick=tick,
                    vector=item.vector.tolist(),
                    payload=item.payload,
                )
            )
        except Exception as exc:
            logger.debug(
                "Promotion check failed",
                extra={"item_id": item_id, "error": str(exc)},
            )
    except Exception as exc:
        logger.debug(
            "Promotion check failed",
            extra={"item_id": item_id, "error": str(exc)},
        )


def check_all_items_for_promotion(
    promoter: "WMLTMPromoter",
    items: List["WMItem"],
    item_ids: List[str],
    tick: int,
    compute_salience_fn,
) -> None:
    """Check all items in working memory for promotion eligibility.

    Per Requirement A2.1: Items with salience >= 0.85 for 3+ consecutive
    ticks are promoted to LTM. This function should be called each cognitive
    cycle to check promotion eligibility.

    Args:
        promoter: WMLTMPromoter instance for handling promotions.
        items: List of working memory items.
        item_ids: List of item IDs for persistence tracking.
        tick: Current tick count.
        compute_salience_fn: Function to compute salience for an item.
    """
    for idx, item in enumerate(items):
        salience = compute_salience_fn(item)
        item_id = item_ids[idx] if idx < len(item_ids) else f"wm_{idx}_{item.tick}"
        check_promotion(promoter, item_id, salience, tick, item)
