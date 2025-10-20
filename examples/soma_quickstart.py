from somafractalmemory.factory import create_memory_system, MemoryMode
from somafractalmemory.core import MemoryType


def main():
    # Simple in-memory setup (no external services needed)
    config = {"redis": {"testing": True}, "vector": {"backend": "inmemory"}}
    mem = create_memory_system(MemoryMode.ON_DEMAND, "demo_ns", config=config)

    # Store an episodic memory
    coord = (1.0, 2.0, 3.0)
    payload = {"task": "write docs", "importance": 2, "memory_type": MemoryType.EPISODIC.value, "timestamp": 0}
    mem.store_memory(coord, payload, memory_type=MemoryType.EPISODIC)

    # Recall via hybrid search
    results = mem.recall("write documentation", top_k=3)
    print("Recall count:", len(results))
    if results:
        print("Top result:", results[0])


if __name__ == "__main__":
    main()

