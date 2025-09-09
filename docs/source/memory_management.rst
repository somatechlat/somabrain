Memory Management
=================

Features
--------
- Store, recall, delete, and link memories
- Filter by type, importance, timestamp, or custom fields
- Use semantic search for natural language queries
- Prune or consolidate memories for efficiency

Advanced Usage
--------------
- Batch operations: store, recall, delete many
- Graph-based linking and shortest path queries
- Export/import memories for backup or migration

Example
-------
.. code-block:: python

   # Store a memory
   payload = {"task": "meeting notes", "importance": 1, "memory_type": "episodic"}
   # POST to /remember

   # Delete a memory
   # POST to /delete with coordinate
