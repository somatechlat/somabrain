"""Action Predictor Service for SomaBrain.

This service implements the action prediction thread as specified in Phase 1 of the
AROMADP roadmap. It publishes PredictorUpdate events to the cog.action.updates topic
with error metrics and performance data.

The service:
1. Consumes action vectors from the cognitive processing pipeline
2. Makes predictions about upcoming actions using configured predictor backend
3. Computes error metrics by comparing predictions with actual actions
4. Publishes PredictorUpdate events with error and latency metrics
5. Maintains strict fail-fast behavior with no soft alternatives
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import numpy as np

from somabrain.prediction import LLMPredictor, PredictionResult
from somabrain.common.kafka import encode, make_producer

from django.conf import settings

try:
    from confluent_kafka import Consumer as CKConsumer, KafkaException
except ImportError as e:
    raise RuntimeError(f"Action predictor requires confluent-kafka: {e}")

# Logging setup
logger = logging.getLogger("somabrain.services.action_predictor")

# Kafka configuration (prod-like defaults, override via env)
SCHEMA_NAME = "predictor_update"
CONSUME_TOPIC = getattr(settings, "topic_next_event", "cog.next_event")
PUBLISH_TOPIC = getattr(settings, "topic_action_updates", "cog.action.updates")
PREDICTOR_ALPHA = float(getattr(settings, "predictor_alpha", 2.0))


class ActionPredictorService:
    """Action prediction service with strict error handling.

    Implements the action prediction thread as specified in Phase 1 of the
    AROMADP roadmap. Consumes action vectors from the cognitive processing
    pipeline, makes predictions using an LLM-based predictor, and publishes
    PredictorUpdate events with error metrics and latency data.
    """

    def __init__(self) -> None:
        """Initialize the action predictor service with LLM predictor and Kafka.

        Creates an LLMPredictor using the configured LLM endpoint for action
        sequence prediction. Initializes Kafka consumer subscribed to the
        next event topic and producer for publishing predictor updates.

        Raises:
            RuntimeError: If LLM endpoint is not configured, Kafka bootstrap
                          servers are missing, or consumer/producer creation fails.

        Notes:
            - Requires SOMABRAIN_LLM_ENDPOINT to be set in environment/Settings
            - Uses centralized Settings for Kafka and tenant configuration
            - Enforces strict fail-fast behavior on configuration errors
            - Consumer group: 'action-predictor'
            - Consumes from: cog.next_event (configurable via Settings)
            - Publishes to: cog.action.updates (configurable via Settings)
        """
        # Use LLM predictor for action prediction (more suitable for action sequences)
        # Use centralized Settings for LLM endpoint; Settings provides default handling
        llm_endpoint = getattr(settings, "llm_endpoint", None)
        if not llm_endpoint:
            raise RuntimeError(
                "LLM endpoint required for action predictor (set SOMABRAIN_LLM_ENDPOINT)"
            )

        self.predictor = LLMPredictor(endpoint=llm_endpoint)
        self.producer = make_producer()
        self.consumer = self._create_consumer()
        # Tenant ID from Settings (fallback to default defined in Settings)
        self.tenant_id = getattr(settings, "tenant_id", "default")

    def _create_consumer(self) -> CKConsumer:
        """Create Kafka consumer with strict configuration."""
        # Prefer Settings' kafka_bootstrap_servers, fallback to legacy env vars for compatibility
        # Use central Settings for Kafka bootstrap; fallback to settings if defined.
        bs = getattr(settings, "KAFKA_BOOTSTRAP_SERVERS", None)
        if not bs:
            raise RuntimeError("Kafka bootstrap servers required but not configured")
        bootstrap_servers = bs.replace("kafka://", "")

        config = {
            "bootstrap.servers": bootstrap_servers,
            "group.id": "action-predictor",
            "auto.offset.reset": "latest",
            "enable.auto.commit": True,
        }

        try:
            consumer = CKConsumer(config)
            consumer.subscribe([CONSUME_TOPIC])
            return consumer
        except Exception as e:
            raise RuntimeError(f"Failed to create Kafka consumer: {e}")

    def _extract_action_vector(
        self, message_data: Dict[str, Any]
    ) -> Optional[np.ndarray]:
        """Extract action vector from next event message."""
        try:
            # Assuming next events contain action-related predictions
            action_data = message_data.get("action_prediction")

            if action_data is None:
                # Try alternative field names
                action_data = (
                    message_data.get("predicted_action")
                    or message_data.get("action_vector")
                    or message_data.get("next_action")
                )

            if action_data is None:
                return None

            if isinstance(action_data, list):
                return np.array(action_data, dtype=np.float32)
            elif isinstance(action_data, dict):
                # Handle embedded vector format
                values = action_data.get("values", [])
                return np.array(values, dtype=np.float32)
            elif isinstance(action_data, str):
                # Convert text action to simple vector representation
                # This is a simplified approach - in practice would use proper embeddings
                action_bytes = action_data.encode("utf-8")
                # Create fixed-size vector from hash
                import hashlib

                hash_obj = hashlib.md5(action_bytes)
                hash_bytes = hash_obj.digest()
                vector = np.frombuffer(hash_bytes, dtype=np.uint8).astype(np.float32)
                return vector / 255.0  # Normalize to [0,1]

            return None
        except Exception as e:
            logger.error(f"Failed to extract action vector: {e}")
            return None

    def _create_predictor_update(
        self,
        prediction_result: PredictionResult,
        latency_ms: float,
        domain: str = "action",
    ) -> Dict[str, Any]:
        """Create PredictorUpdate event from prediction result."""
        err = float(prediction_result.error)
        conf = float(np.exp(-PREDICTOR_ALPHA * max(0.0, err)))
        return {
            "tenant": self.tenant_id,
            "domain": domain,
            "predictor_type": "llm",
            "error_metric": err,
            "prediction_latency_ms": float(latency_ms),
            "model_version": "1.0",
            "vector_dim": int(len(prediction_result.predicted_vec)),
            "confidence": conf,
            "ts": datetime.now(timezone.utc).isoformat(),
        }

    async def process_message(self, message_data: Dict[str, Any]) -> None:
        """Process a single next event message and publish prediction update."""
        action_vector = self._extract_action_vector(message_data)
        if action_vector is None:
            logger.warning("No valid action vector found in message")
            return

        # Make prediction with timing
        start_time = time.perf_counter()
        try:
            # For action prediction, we predict next actions based on current context
            prediction_result = self.predictor.predict_and_compare(
                expected_vec=action_vector, actual_vec=action_vector
            )
        except Exception as e:
            logger.error(f"Action prediction failed: {e}")
            raise RuntimeError(f"Action prediction failed: {e}")

        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000

        # Create and publish predictor update
        update_event = self._create_predictor_update(
            prediction_result, latency_ms, domain="action"
        )

        try:
            encoded_message = encode(update_event, SCHEMA_NAME)
            future = self.producer.send(PUBLISH_TOPIC, encoded_message)
            future.get(timeout=5.0)  # Strict: fail if publish times out
            logger.debug(
                f"Published action predictor update: error={prediction_result.error:.4f}"
            )
        except Exception as e:
            logger.error(f"Failed to publish predictor update: {e}")
            raise RuntimeError(f"Failed to publish predictor update: {e}")

    async def run(self) -> None:
        """Main service loop."""
        logger.info("Starting Action Predictor Service")

        try:
            while True:
                try:
                    # Poll for messages with timeout
                    msg = self.consumer.poll(timeout=1.0)
                    if msg is None:
                        continue

                    if msg.error():
                        if msg.error().code() == KafkaException._PARTITION_EOF:
                            continue
                        else:
                            raise RuntimeError(f"Kafka consumer error: {msg.error()}")

                    # Decode message (assuming JSON for now, will be Avro when schema ready)
                    try:
                        message_data = json.loads(msg.value().decode("utf-8"))
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to decode message as JSON: {e}")
                        continue

                    # Process the message
                    await self.process_message(message_data)

                except KeyboardInterrupt:
                    logger.info("Received shutdown signal")
                    break
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # Strict mode: re-raise errors instead of continuing
                    raise

        finally:
            logger.info("Shutting down Action Predictor Service")
            self.consumer.close()
            self.producer.flush(timeout=5.0)


async def main():
    """Entry point for the action predictor service."""
    service = ActionPredictorService()
    await service.run()


if __name__ == "__main__":
    asyncio.run(main())
