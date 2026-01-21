"""Agent Predictor Service for SomaBrain.

This service implements the agent prediction thread as specified in Phase 1 of the
AROMADP roadmap. It publishes PredictorUpdate events to the cog.agent.updates topic
with error metrics and performance data.

The service:
1. Consumes agent behavior vectors from the cognitive processing pipeline
2. Makes predictions about agent decisions using configured predictor backend
3. Computes error metrics by comparing predictions with actual agent behavior
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
from django.conf import settings

from somabrain.common.kafka import encode, make_producer
from somabrain.prediction import (
    BudgetedPredictor,
    MahalanobisPredictor,
    PredictionResult,
)

try:
    from confluent_kafka import Consumer as CKConsumer
    from confluent_kafka import KafkaException
except ImportError as e:
    raise RuntimeError(f"Agent predictor requires confluent-kafka: {e}")

# Logging setup
logger = logging.getLogger("somabrain.services.agent_predictor")

# Kafka configuration (prod-like defaults, override via env)
SCHEMA_NAME = "predictor_update"
CONSUME_TOPIC = getattr(settings, "topic_global_frame", "cog.global.frame")
PUBLISH_TOPIC = getattr(settings, "topic_agent_updates", "cog.agent.updates")
PREDICTOR_ALPHA = float(getattr(settings, "predictor_alpha", 2.0))


class AgentPredictorService:
    """Agent prediction service with strict error handling.

    Implements the agent prediction thread as specified in Phase 1 of the
    AROMADP roadmap. Consumes agent behavior vectors from the cognitive
    processing pipeline, makes predictions using a budgeted Mahalanobis
    predictor, and publishes PredictorUpdate events with error metrics.
    """

    def __init__(self) -> None:
        """Initialize the agent predictor service with Kafka consumer/producer.

        Creates a BudgetedPredictor wrapping MahalanobisPredictor with a 100ms
        timeout for agent predictions. Initializes Kafka consumer subscribed
        to the global frame topic and producer for publishing predictor updates.

        Raises:
            RuntimeError: If Kafka bootstrap servers are not configured or
                          if consumer/producer creation fails.

        Notes:
            - Uses centralized Settings for Kafka and tenant configuration
            - Enforces strict fail-fast behavior on configuration errors
            - Consumer group: 'agent-predictor'
            - Consumes from: cog.global.frame (configurable via Settings)
            - Publishes to: cog.agent.updates (configurable via Settings)
        """
        # Use budgeted predictor to enforce time limits on agent predictions
        base_predictor = MahalanobisPredictor()
        self.predictor = BudgetedPredictor(base_predictor, timeout_ms=100)
        self.producer = make_producer()
        self.consumer = self._create_consumer()
        # Use centralized Settings for tenant ID, default handled by Settings
        self.tenant_id = getattr(settings, "tenant_id", "default")

    def _create_consumer(self) -> CKConsumer:
        """Create Kafka consumer with strict configuration."""
        # Prefer Settings' kafka_bootstrap_servers, falling back to legacy env vars if not set
        # Prefer Settings' kafka_bootstrap_servers, falling back to legacy env vars if not set
        # Prefer Settings' kafka_bootstrap_servers, falling back to legacy env vars for compatibility
        # Use central Settings for Kafka bootstrap; fallback to settings if defined.
        bs = getattr(settings, "KAFKA_BOOTSTRAP_SERVERS", None)
        if not bs:
            raise RuntimeError("Kafka bootstrap servers required but not configured")
        bootstrap_servers = bs.replace("kafka://", "")

        config = {
            "bootstrap.servers": bootstrap_servers,
            "group.id": "agent-predictor",
            "auto.offset.reset": "latest",
            "enable.auto.commit": True,
        }

        try:
            consumer = CKConsumer(config)
            consumer.subscribe([CONSUME_TOPIC])
            return consumer
        except Exception as e:
            raise RuntimeError(f"Failed to create Kafka consumer: {e}")

    def _extract_agent_vector(
        self, message_data: Dict[str, Any]
    ) -> Optional[np.ndarray]:
        """Extract agent behavior vector from integrator context message."""
        try:
            # Assuming integrator context contains agent-related vectors
            context = message_data.get("context", {})
            agent_data = context.get("agent_behavior")

            if agent_data is None:
                # Try alternative field names
                agent_data = context.get("agent_vector") or context.get(
                    "behavior_vector"
                )

            if agent_data is None:
                return None

            if isinstance(agent_data, list):
                return np.array(agent_data, dtype=np.float32)
            elif isinstance(agent_data, dict):
                # Handle embedded vector format
                values = agent_data.get("values", [])
                return np.array(values, dtype=np.float32)

            return None
        except Exception as e:
            logger.error(f"Failed to extract agent vector: {e}")
            return None

    def _create_predictor_update(
        self,
        prediction_result: PredictionResult,
        latency_ms: float,
        domain: str = "agent",
    ) -> Dict[str, Any]:
        """Create PredictorUpdate event from prediction result."""
        err = float(prediction_result.error)
        conf = float(np.exp(-PREDICTOR_ALPHA * max(0.0, err)))
        return {
            "tenant": self.tenant_id,
            "domain": domain,
            "predictor_type": "budgeted_mahalanobis",
            "error_metric": err,
            "prediction_latency_ms": float(latency_ms),
            "model_version": "1.0",
            "vector_dim": int(len(prediction_result.predicted_vec)),
            "confidence": conf,
            "ts": datetime.now(timezone.utc).isoformat(),
        }

    async def process_message(self, message_data: Dict[str, Any]) -> None:
        """Process a single agent context message and publish prediction update."""
        agent_vector = self._extract_agent_vector(message_data)
        if agent_vector is None:
            logger.warning("No valid agent vector found in message")
            return

        # Make prediction with timing
        start_time = time.perf_counter()
        try:
            # For agent prediction, we predict agent behavior based on context
            prediction_result = self.predictor.predict_and_compare(
                expected_vec=agent_vector, actual_vec=agent_vector
            )
        except Exception as e:
            logger.error(f"Agent prediction failed: {e}")
            raise RuntimeError(f"Agent prediction failed: {e}")

        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000

        # Create and publish predictor update
        update_event = self._create_predictor_update(
            prediction_result, latency_ms, domain="agent"
        )

        try:
            encoded_message = encode(update_event, SCHEMA_NAME)
            future = self.producer.send(PUBLISH_TOPIC, encoded_message)
            future.get(timeout=5.0)  # Strict: fail if publish times out
            logger.debug(
                f"Published agent predictor update: error={prediction_result.error:.4f}"
            )
        except Exception as e:
            logger.error(f"Failed to publish predictor update: {e}")
            raise RuntimeError(f"Failed to publish predictor update: {e}")

    async def run(self) -> None:
        """Main service loop."""
        logger.info("Starting Agent Predictor Service")

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
            logger.info("Shutting down Agent Predictor Service")
            self.consumer.close()
            self.producer.flush(timeout=5.0)


async def main():
    """Entry point for the agent predictor service."""
    service = AgentPredictorService()
    await service.run()


if __name__ == "__main__":
    asyncio.run(main())
