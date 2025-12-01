import unittest
from unittest.mock import patch, MagicMock
from somabrain.milvus_client import MilvusClient


class TestMilvusClient(unittest.TestCase):
    pass


@patch("somabrain.milvus_client.connections")
@patch("somabrain.milvus_client.utility")
@patch("somabrain.milvus_client.Collection")
def test_init_creates_collection_if_missing(
    mock_collection, mock_utility, mock_connections
):
    """Ensure the client attempts to create a collection when missing.

    The test patches the Milvus SDK components and verifies that the client
    connects and calls the appropriate SDK helpers. ``self`` is not used because
    these are plain test functions, not ``unittest.TestCase`` methods.
    """
    # Setup mocks
    mock_utility.has_collection.return_value = False
    mock_conn = MagicMock()
    mock_connections.connect.return_value = mock_conn
    # Instantiate client – we only care about side‑effects.
    _ = MilvusClient()
    # Verify connection called with defaults
    mock_connections.connect.assert_called()
    # Verify collection creation called
    assert mock_utility.has_collection.called
    assert mock_collection.called


@patch("somabrain.milvus_client._vector_from_payload")
@patch("somabrain.milvus_client.MilvusClient.collection")
def test_upsert_option_calls_insert(mock_collection, mock_vector):
    """Validate that ``upsert_option`` inserts and flushes the collection."""
    mock_vector.return_value = [0.0] * 128
    client = MilvusClient()
    client.collection = mock_collection
    client.upsert_option("t1", "opt1", b"data")
    mock_collection.insert.assert_called()
    mock_collection.flush.assert_called()


@patch("somabrain.milvus_client._vector_from_payload")
@patch("somabrain.milvus_client.MilvusClient.collection")
def test_search_similar_uses_settings_defaults(mock_collection, mock_vector):
    """Check that ``search_similar`` respects default settings values.

    The mock collection returns a fabricated search result; the test asserts the
    returned list structure and content.
    """
    mock_vector.return_value = [0.0] * 128
    mock_search_result = MagicMock()
    hit = MagicMock()
    hit.distance = 0.2
    hit.entity.get.return_value = "opt123"
    mock_search_result.__getitem__.return_value = [hit]
    mock_collection.search.return_value = mock_search_result
    client = MilvusClient()
    client.collection = mock_collection
    results = client.search_similar("t1", b"data")
    assert isinstance(results, list)
    assert results[0][0] == "opt123"


if __name__ == "__main__":
    unittest.main()
