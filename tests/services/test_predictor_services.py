"""Integration test for predictor services.

This test verifies that the state, agent, and action predictor services
can be instantiated and their core methods work correctly.
"""

import json
import numpy as np
import pytest
from unittest.mock import Mock, patch

from somabrain.services.state_predictor import StatePredictorService
from somabrain.services.agent_predictor import AgentPredictorService
from somabrain.services.action_predictor import ActionPredictorService


class TestPredictorServices:
    """Test suite for predictor services."""

    @patch('somabrain.common.kafka.make_producer')
    @patch('confluent_kafka.Consumer')
    def test_state_predictor_initialization(self, mock_consumer, mock_producer):
        """Test state predictor service can be initialized."""
        mock_producer.return_value = Mock()
        mock_consumer.return_value = Mock()
        
        service = StatePredictorService()
        assert service is not None
        assert service.predictor is not None
        assert service.tenant_id == "default"

    @patch('somabrain.common.kafka.make_producer') 
    @patch('confluent_kafka.Consumer')
    def test_agent_predictor_initialization(self, mock_consumer, mock_producer):
        """Test agent predictor service can be initialized."""
        mock_producer.return_value = Mock()
        mock_consumer.return_value = Mock()
        
        service = AgentPredictorService()
        assert service is not None
        assert service.predictor is not None
        assert service.tenant_id == "default"

    @patch('somabrain.common.kafka.make_producer')
    @patch('confluent_kafka.Consumer')
    @patch.dict('os.environ', {'SOMABRAIN_LLM_ENDPOINT': 'http://test-llm:8080'})
    def test_action_predictor_initialization(self, mock_consumer, mock_producer):
        """Test action predictor service can be initialized with LLM endpoint.""" 
        mock_producer.return_value = Mock()
        mock_consumer.return_value = Mock()
        
        service = ActionPredictorService()
        assert service is not None
        assert service.predictor is not None
        assert service.tenant_id == "default"

    def test_action_predictor_requires_llm_endpoint(self):
        """Test action predictor fails without LLM endpoint."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(RuntimeError, match="LLM endpoint required"):
                ActionPredictorService()

    def test_state_vector_extraction(self):
        """Test state vector extraction from global frame messages."""
        with patch('somabrain.common.kafka.make_producer'), \
             patch('confluent_kafka.Consumer'):
            
            service = StatePredictorService()
            
            # Test valid vector data
            message_data = {
                "state_vector": [1.0, 2.0, 3.0, 4.0]
            }
            vector = service._extract_state_vector(message_data)
            assert vector is not None
            assert len(vector) == 4
            np.testing.assert_array_equal(vector, [1.0, 2.0, 3.0, 4.0])

            # Test embedded vector format
            message_data = {
                "state_vector": {
                    "values": [0.5, 1.5, 2.5]
                }
            }
            vector = service._extract_state_vector(message_data)
            assert vector is not None
            assert len(vector) == 3

            # Test missing vector
            message_data = {}
            vector = service._extract_state_vector(message_data)
            assert vector is None

    def test_agent_vector_extraction(self):
        """Test agent vector extraction from integrator context messages."""
        with patch('somabrain.common.kafka.make_producer'), \
             patch('confluent_kafka.Consumer'):
            
            service = AgentPredictorService()
            
            # Test valid agent behavior data
            message_data = {
                "context": {
                    "agent_behavior": [0.1, 0.2, 0.3]
                }
            }
            vector = service._extract_agent_vector(message_data)
            assert vector is not None
            assert len(vector) == 3

            # Test alternative field name
            message_data = {
                "context": {
                    "agent_vector": [1.1, 1.2, 1.3, 1.4]
                }
            }
            vector = service._extract_agent_vector(message_data)
            assert vector is not None
            assert len(vector) == 4

    @patch.dict('os.environ', {'SOMABRAIN_LLM_ENDPOINT': 'http://test-llm:8080'})
    def test_action_vector_extraction(self):
        """Test action vector extraction from next event messages."""
        with patch('somabrain.common.kafka.make_producer'), \
             patch('confluent_kafka.Consumer'):
            
            service = ActionPredictorService()
            
            # Test list action data
            message_data = {
                "action_prediction": [2.0, 3.0, 4.0, 5.0]
            }
            vector = service._extract_action_vector(message_data)
            assert vector is not None
            assert len(vector) == 4

            # Test string action data (gets converted to hash vector)
            message_data = {
                "predicted_action": "move_forward"
            }
            vector = service._extract_action_vector(message_data)
            assert vector is not None
            assert len(vector) == 16  # MD5 hash produces 16 bytes

    def test_predictor_update_creation(self):
        """Test predictor update event creation."""
        with patch('somabrain.common.kafka.make_producer'), \
             patch('confluent_kafka.Consumer'):
            
            service = StatePredictorService()
            
            # Mock prediction result
            predicted_vec = np.array([1.0, 2.0, 3.0])
            actual_vec = np.array([1.1, 2.1, 3.1])
            
            from somabrain.prediction import PredictionResult
            result = PredictionResult(
                predicted_vec=predicted_vec,
                actual_vec=actual_vec,
                error=0.15
            )
            
            update = service._create_predictor_update(result, 25.5, "test_domain")
            
            assert update["tenant"] == "default"
            assert update["domain"] == "test_domain"
            assert update["predictor_type"] == "mahalanobis"
            assert update["error_metric"] == 0.15
            assert update["prediction_latency_ms"] == 25.5
            assert update["vector_dim"] == 3
            assert update["confidence"] == 0.85  # 1.0 - error
            assert "ts" in update