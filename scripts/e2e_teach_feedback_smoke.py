from __future__ import annotations
import json
from common.config.settings import settings
import sys
import time
from typing import Any, Dict, Optional
from common.logging import logger
from kafka import KafkaProducer, KafkaConsumer  # type: ignore
from libs.kafka_cog.avro_schemas import load_schema  # type: ignore
from libs.kafka_cog.serde import AvroSerde  # type: ignore

#!/usr/bin/env python3
"""
E2E smoke: TeachFeedback -> RewardEvent

Procedure:
    pass
- Produce a TeachFeedback JSON record to topic cog.teach.feedback
- Consume from cog.reward.events and verify a RewardEvent appears with the same frame_id

Notes:
    pass
- The processor may emit Avro-schemaless or JSON; we try Avro first (if fastavro available)
"""


try:
    pass
except Exception as exc:
    logger.exception("Exception caught: %s", exc)
    raise
except Exception as exc:
    logger.exception("Exception caught: %s", exc)
    raise

try:
    pass
except Exception as exc:
    logger.exception("Exception caught: %s", exc)
    raise
except Exception as exc:
    logger.exception("Exception caught: %s", exc)
    raise


TEACH_TOPIC = "cog.teach.feedback"
REWARD_TOPIC = "cog.reward.events"


def _bootstrap() -> str:
    url = settings.kafka_bootstrap_servers or "kafka://127.0.0.1:30102"
    return str(url).replace("kafka://", "")


def _avro_reward_serde() -> Optional[AvroSerde]:
    if load_schema is None or AvroSerde is None:
        return None
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        return AvroSerde(load_schema("reward_event"))  # type: ignore[arg-type]
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        return None


def _decode_reward(value: bytes) -> Optional[Dict[str, Any]]:
    # Try Avro first
    serde = _avro_reward_serde()
    if serde is not None:
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            out = serde.deserialize(value)  # type: ignore[arg-type]
            if isinstance(out, dict):
                return out
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
    raise
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        return json.loads(value.decode("utf-8"))
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        return None


def produce_teach_feedback(prod: KafkaProducer, frame_id: str) -> None:
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rec = {
        "feedback_id": f"fb-{int(time.time()*1000)}",
        "capsule_id": f"cap-{int(time.time()*1000)}",
        "frame_id": frame_id,
        "ts": now_iso,
        "rating": 5,
        "comment": "smoke-test",
    }
    payload = json.dumps(rec).encode("utf-8")
    fut = prod.send(TEACH_TOPIC, value=payload)
    fut.get(timeout=10)


def consume_reward_for_frame(
    consumer: KafkaConsumer, frame_id: str, timeout_s: int = 60
) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        msg = consumer.poll(timeout_ms=500)
        if msg is None:
            continue
        if isinstance(msg, dict):
            records = []
            for _, v in msg.items():
                records.extend(v)
        else:
            records = [msg]
        for r in records:
            val = getattr(r, "value", None)
            if not val:
                continue
            dec = _decode_reward(val)
            if isinstance(dec, dict):
                if str(dec.get("frame_id") or "").strip() == frame_id:
                    return True
    return False


def main() -> None:
    bootstrap = _bootstrap()
    frame_id = f"frame-{int(time.time()*1000)}"

    prod = KafkaProducer(bootstrap_servers=bootstrap, value_serializer=lambda v: v)
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        produce_teach_feedback(prod, frame_id)
    finally:
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            prod.flush(5)
            prod.close()
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
    raise

    cons = KafkaConsumer(
        REWARD_TOPIC,
        bootstrap_servers=bootstrap,
        value_deserializer=lambda m: m,
        auto_offset_reset="latest",
        enable_auto_commit=False,
        group_id=f"teach-smoke-{int(time.time())}",
        consumer_timeout_ms=1000, )
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        ok = consume_reward_for_frame(cons, frame_id, timeout_s=90)
    finally:
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            cons.close()
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
    raise

    if not ok:
        print(
            "Teach->Reward smoke failed: no matching reward received", file=sys.stderr
        )
        sys.exit(1)
    print("Teach->Reward smoke passed.")


if __name__ == "__main__":
    main()
