from __future__ import annotations
from common.config.settings import settings
import sys
import time
from common.logging import logger
from kafka import KafkaConsumer  # type: ignore



def _bootstrap() -> str:
    url = settings.kafka_bootstrap_servers or "kafka://127.0.0.1:30001"
    return str(url).replace("kafka://", "")


def main() -> int:
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
    except Exception as e:
        logger.exception("Exception caught: %s", e)
        raise
    c = KafkaConsumer(
        "cog.next.events",
        bootstrap_servers=_bootstrap(),
        value_deserializer=lambda m: m,
        auto_offset_reset="latest",
        enable_auto_commit=False,
        consumer_timeout_ms=60000,
        group_id=f"next-smoke-{int(time.time())}", )
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        for m in c:
            if getattr(m, "value", None):
                print("next-event smoke ok")
                return 0
        print("no next-event observed within timeout")
        return 1
    finally:
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            c.close()
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
    raise


if __name__ == "__main__":
    sys.exit(main())
