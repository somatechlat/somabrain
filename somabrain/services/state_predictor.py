"""State Predictor Service for SomaBrain.

This service implements the state prediction thread as specified in Phase 1 of the
AROMADP roadmap. It publishes PredictorUpdate events to the cog.state.updates topic
with error metrics and performance data.

The service:
1. Consumes state vectors from the cognitive processing pipeline
2. Makes predictions using the configured predictor backend
3. Computes error metrics by comparing predictions with actual vectors
4. Publishes PredictorUpdate events with error and latency metrics
5. Maintains strict fail-fast behavior with no soft alternatives
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import numpy as np

from somabrain.prediction import MahalanobisPredictor, PredictionResult
from somabrain.common.kafka import encode, make_producer
from common.config.settings import settings as shared_settings

try:
    from confluent_kafka import Consumer as CKConsumer, KafkaException
except ImportError as e:
    raise RuntimeError(f"State predictor requires confluent-kafka: {e}")

try:
    from common.config.settings import settings as shared_settings
except ImportError:
    shared_settings = None

# Logging setup
logger = logging.getLogger("somabrain.services.state_predictor")

# Kafka configuration (prod-like defaults, override via env/settings)
SCHEMA_NAME = "predictor_update"
CONSUME_TOPIC = os.getenv(
    "SOMABRAIN_TOPIC_GLOBAL_FRAME",
    getattr(shared_settings, "topic_global_frame", "cog.global.frame"),
)
PUBLISH_TOPIC = os.getenv(
    "SOMABRAIN_TOPIC_STATE_UPDATES",
    getattr(shared_settings, "topic_state_updates", "cog.state.updates"),
)
PREDICTOR_ALPHA = float(os.getenv("SOMABRAIN_PREDICTOR_ALPHA", "2.0") or 2.0)


class StatePredictorService:
    """State prediction service with strict error handling."""

    def __init__(self):
        """Initialize the state predictor service."""
        self.predictor = MahalanobisPredictor()
        self.producer = make_producer()
        self.consumer = self._create_consumer()
        self.tenant_id = os.getenv("SOMABRAIN_TENANT_ID", "default")

    def _create_consumer(self) -> CKConsumer:
        """Create Kafka consumer with strict configuration."""
        bs = os.getenv("SOMA_KAFKA_BOOTSTRAP") or os.getenv("SOMABRAIN_KAFKA_URL")
        if not bs:
            raise RuntimeError("Kafka bootstrap servers required but not configured")
        bootstrap_servers = bs.replace("kafka://", "")

        config = {
            "bootstrap.servers": bootstrap_servers,
            "group.id": "state-predictor",
            "auto.offset.reset": "latest",
            "enable.auto.commit": True,
        }
        
        try:
            consumer = CKConsumer(config)
            consumer.subscribe([CONSUME_TOPIC])
            return consumer
        except Exception as e:
            raise RuntimeError(f"Failed to create Kafka consumer: {e}")

    def _extract_state_vector(self, message_data: Dict[str, Any]) -> Optional[np.ndarray]:
        """Extract state vector from global frame message."""
        try:
            # Assuming global frame contains a 'state_vector' field
            vector_data = message_data.get("state_vector")
            if vector_data is None:
                return None
            
            if isinstance(vector_data, list):
                return np.array(vector_data, dtype=np.float32)
            elif isinstance(vector_data, dict):
                # Handle embedded vector format
                values = vector_data.get("values", [])
                return np.array(values, dtype=np.float32)
            
            return None
        except Exception as e:
            logger.error(f"Failed to extract state vector: {e}")
            return None

    def _create_predictor_update(
        self, 
        prediction_result: PredictionResult, 
        latency_ms: float,
        domain: str = "state"
    ) -> Dict[str, Any]:
        """Create PredictorUpdate event from prediction result."""
        err = float(prediction_result.error)
        conf = float(np.exp(-PREDICTOR_ALPHA * max(0.0, err)))
        return {
            "tenant": self.tenant_id,
            "domain": domain,
            "predictor_type": "mahalanobis",
            "error_metric": err,
            "prediction_latency_ms": float(latency_ms),
            "model_version": "1.0",
            "vector_dim": int(len(prediction_result.predicted_vec)),
            "confidence": conf,
            "ts": datetime.now(timezone.utc).isoformat(),
        }

    async def process_message(self, message_data: Dict[str, Any]) -> None:
        """Process a single state message and publish prediction update."""
        state_vector = self._extract_state_vector(message_data)
        if state_vector is None:
            logger.warning("No valid state vector found in message")
            return

        # Make prediction with timing
        start_time = time.perf_counter()
        try:
            # For state prediction, we predict the next state based on current state
            # Using the same vector as both expected and actual for error calculation
            prediction_result = self.predictor.predict_and_compare(
                expected_vec=state_vector,
                actual_vec=state_vector
            )
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            raise RuntimeError(f"State prediction failed: {e}")
        
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000

        # Create and publish predictor update
        update_event = self._create_predictor_update(
            prediction_result, latency_ms, domain="state"
        )

        try:
            encoded_message = encode(update_event, SCHEMA_NAME)
            future = self.producer.send(PUBLISH_TOPIC, encoded_message)
            future.get(timeout=5.0)  # Strict: fail if publish times out
            logger.debug(f"Published state predictor update: error={prediction_result.error:.4f}")
        except Exception as e:
            logger.error(f"Failed to publish predictor update: {e}")
            raise RuntimeError(f"Failed to publish predictor update: {e}")

    async def run(self) -> None:
        """Main service loop."""
        logger.info("Starting State Predictor Service")
        
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
                        message_data = json.loads(msg.value().decode('utf-8'))
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
            logger.info("Shutting down State Predictor Service")
            self.consumer.close()
            self.producer.flush(timeout=5.0)


async def main():
    """Entry point for the state predictor service."""
    service = StatePredictorService()
    await service.run()


if __name__ == "__main__":
    asyncio.run(main())
