.. SOMABRAIN documentation master file, created by
   sphinx-quickstart on Mon Sep  1 20:19:54 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

SOMABRAIN documentation
=======================

Welcome to the SOMABRAIN documentation!

SOMABRAIN is a cognitive memory system for agents and applications. It provides:

- Persistent, context-aware memory storage and recall
- Fast semantic search and retrieval
- Flexible API for agents, chatbots, and automation

Quickstart
----------

- To store a memory, use the `/remember` endpoint or CLI:

  Example:

  .. code-block:: bash

     curl -X POST http://127.0.0.1:9898/remember \
       -H "Content-Type: application/json" \
       -d '{"coord": null, "payload": {"task": "Test memory creation", "importance": 1, "memory_type": "episodic"}}'

- To recall a memory, use the `/recall` endpoint:

  .. code-block:: bash

     curl -X POST http://127.0.0.1:9898/recall \
       -H "Content-Type: application/json" \
       -d '{"query": "Test memory creation"}'

Memory Schema
-------------

.. code-block:: python

   {
     "coordinate": [1.0, 2.0, 3.0],
     "memory_type": "episodic",
     "timestamp": 1693593600.0,
     "importance": 1,
     "task": "write documentation",
     "links": [
       {"to": [4.0, 5.0, 6.0], "type": "related", "timestamp": 1693593700}
     ]
   }

Timestamp fields are expressed in Unix epoch seconds (float). Clients may send
ISO-8601 strings (e.g., ``"2025-10-03T09:30:00Z"``); the API converts them to
epoch seconds so recall responses and exported payloads remain consistent.

For more details, see the API documentation and guides in this site.


.. toctree::
  :maxdepth: 2
  :caption: Contents

  architecture
  api
  agent_integration

  api_reference
  api_quickstart
  benchmarks
  workbench
  math
  tutorials

  PROJECT_PLAN
  OPERATIONS_RUNBOOK
  AUTONOMOUS_OPERATIONS_GUIDE
  Docker_Configuration_Options_Soma_Brain
  configuration
  memory_management
  modules
  numerics
  developer_memory_setup
  REPORT_NUMERICS_HARDENING
