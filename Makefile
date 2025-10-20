PY := .venv/bin/python

.PHONY: test
test:
	PYTHONPATH=. $(PY) tests/test_endpoints_basic.py
	PYTHONPATH=. $(PY) tests/test_hrr_cleanup.py
	PYTHONPATH=. $(PY) tests/test_memory_client.py
	PYTHONPATH=. $(PY) tests/test_reflection_v2.py
	PYTHONPATH=. $(PY) tests/test_graph_reasoning.py
	PYTHONPATH=. $(PY) tests/test_personality.py
	PYTHONPATH=. $(PY) tests/test_predictor_budget.py
	PYTHONPATH=. $(PY) tests/test_migration.py

