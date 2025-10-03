Memory Management
=================

Features
--------
- Store, recall, delete, and link memories
- Filter by type, importance, timestamp, or custom fields
- Use semantic search for natural language queries
- Prune or consolidate memories for efficiency

Timestamp fields across the API are expressed as Unix epoch seconds (float).
When writing data you may pass either epoch seconds or ISO-8601 strings; the
service converts them to epoch seconds for storage and recall responses.

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
