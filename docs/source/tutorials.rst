Tutorials & Scenarios
=====================

Tutorial 1: Storing and Recalling a Memory
------------------------------------------
.. code-block:: bash

   curl -X POST http://127.0.0.1:9696/remember \
     -H "Content-Type: application/json" \
     -d '{"coord": null, "payload": {"task": "First memory", "importance": 1, "memory_type": "episodic"}}'

   curl -X POST http://127.0.0.1:9696/recall \
     -H "Content-Type: application/json" \
     -d '{"query": "First memory"}'

Tutorial 2: Agent Context Recall
--------------------------------
.. code-block:: python

   # Store agent context
   payload = {"task": "Agent context", "importance": 2, "memory_type": "semantic"}
   # POST to /remember

   # Recall context
   query = {"query": "Agent context"}
   # POST to /recall
