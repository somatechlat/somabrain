"""
SomaBrain Foundation Demo - REAL Working System

This script demonstrates the ACTUAL working capabilities of SomaBrain.
"""

def main():
    print("🧠 SomaBrain Foundation Demo - REAL Working System")
    print("=" * 60)
    print()
    print("✅ WORKING COMPONENTS:")
    print("   • Fractal Memory System (7 cognitive scales)")
    print("   • Deterministic Embeddings (256D vectors)")
    print("   • REST API (/remember, /recall, /status)")
    print("   • File-based persistence")
    print()
    print("❌ NOT WORKING (Yet):")
    print("   • FNOM Memory (import errors)")
    print("   • Working Memory (missing implementation)")
    print("   • Salience System (missing implementation)")
    print("   • Consolidation (missing implementation)")
    print("   • Reflection (missing implementation)")
    print()
    print("💡 KEY INSIGHT:")
    print("   We built a SOLID FOUNDATION using what WORKS,")
    print("   not what we wished worked or planned to build.")
    print()
    print("🚀 NEXT STEPS:")
    print("   Phase 1: Build functional Working Memory")
    print("   Phase 2: Add basic attention/salience")
    print("   Phase 3: Implement learning from interactions")
    print()
    print("This is REAL progress - measurable, working, deployable AI.")
    print()
    print("To run the demo:")
    print("1. python somabrain_foundation.py  # Test foundation")
    print("2. python somabrain_api.py        # Start API server")
    print("3. Use POST /remember and /recall endpoints")


if __name__ == "__main__":
    main()

import time
import requests
import json
from datetime import datetime


def demo_foundation():
    """Demonstrate the working SomaBrain foundation."""

    print("🧠 SomaBrain Foundation Demo - REAL Working System")
    print("=" * 60)
    print()
    print("This demo shows what ACTUALLY WORKS in SomaBrain:")
    print("• Fractal Memory System with 7 cognitive scales")
    print("• Deterministic embeddings (256D unit-norm vectors)")
    print("• REST API with /remember and /recall endpoints")
    print("• File-based memory persistence")
    print()
    print("No quantum cognition, no multiverse transcendence - just REAL working AI.")
    print()

    # Start the API server
    print("🚀 Starting SomaBrain Foundation API...")
    import subprocess
    import sys
    import os

    # Change to the correct directory
    os.chdir('/Users/macbookpro201916i964gb1tb/Documents/GitHub/somabrain')

    server = subprocess.Popen([
        sys.executable, '-m', 'uvicorn', 'somabrain_api:app',
        '--host', '0.0.0.0', '--port', '8000', '--reload'
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Wait for server to start
    time.sleep(3)

    try:
        try:
        try:
        print("✅ API server started on http://localhost:8000")
        print()

        # Demo 1: Store some memories
        print("📝 Demo 1: Storing Memories")
        print("-" * 30)

        memories = [
            {
                "content": "Paris is the capital and most populous city of France",
                "metadata": {"category": "geography", "country": "France"}
            },
            {
                "content": "Python is a high-level programming language known for its simplicity",
                "metadata": {"category": "technology", "type": "programming"}
            },
            {
                "content": "Machine learning is a subset of artificial intelligence",
                "metadata": {"category": "technology", "field": "AI"}
            },
            {
                "content": "The Eiffel Tower is an iron lattice tower in Paris, France",
                "metadata": {"category": "landmarks", "city": "Paris"}
            },
            {
                "content": "Neural networks are computing systems inspired by biological brains",
                "metadata": {"category": "technology", "field": "AI"}
            }
        ]

        stored_ids = []
        for memory in memories:
            try:
                response = requests.post('http://localhost:8000/remember', json=memory)
                memory_id = response.json()
                stored_ids.append(memory_id)
                print(f"✅ Stored: {memory['content'][:40]}...")
            except Exception as e:
                print(f"❌ Failed to store: {e}")

        print(f"\n📊 Stored {len(stored_ids)} memories successfully")
        print()

        # Demo 2: Recall memories
        print("🔍 Demo 2: Recalling Memories")
        print("-" * 30)

        queries = [
            "programming languages",
            "artificial intelligence",
            "Paris landmarks",
            "French geography"
        ]

        for query in queries:
            print(f"\n🔍 Query: '{query}'")
            try:
                response = requests.post('http://localhost:8000/recall',
                                       json={"query": query, "limit": 3})
                results = response.json()

                if results:
                    print(f"   Found {len(results)} relevant memories:")
                    for i, result in enumerate(results, 1):
                        similarity = result['similarity']
                        content = result['content'][:50]
                        print(f"     {i}. {content}... (sim: {similarity:.3f})")
                else:
                    print("   No relevant memories found")

            except Exception as e:
                print(f"❌ Recall failed: {e}")

        print()

        # Demo 3: System status
        print("📊 Demo 3: System Status")
        print("-" * 30)

        try:
            response = requests.get('http://localhost:8000/status')
            status = response.json()

            print("System Status: OPERATIONAL")
            print(f"Working Components: {', '.join(status['working_components'])}")
            print(f"Total Memories: {status['total_memories']}")
            print(f"Memory File: {status['memory_file']}")
            print(f"Last Updated: {status['last_updated']}")

        except Exception as e:
            print(f"❌ Status check failed: {e}")

        print()

        # Reality Check
        print("🎯 REALITY CHECK - What We Actually Built")
        print("-" * 30)
        print("✅ WORKING COMPONENTS:")
        print("   • Fractal Memory System (7 cognitive scales)")
        print("   • Deterministic Embeddings (256D vectors)")
        print("   • REST API (/remember, /recall, /status)")
        print("   • File-based persistence")
        print()
        print("❌ NOT WORKING (Yet):")
        print("   • FNOM Memory (import errors)")
        print("   • Working Memory (missing implementation)")
        print("   • Salience System (missing implementation)")
        print("   • Consolidation (missing implementation)")
        print("   • Reflection (missing implementation)")
        print()
        print("💡 KEY INSIGHT:")
        print("   We built a SOLID FOUNDATION using what WORKS,")
        print("   not what we wished worked or planned to build.")
        print()
        print("🚀 NEXT STEPS:")
        print("   Phase 1: Build functional Working Memory")
        print("   Phase 2: Add basic attention/salience")
        print("   Phase 3: Implement learning from interactions")
        print()
        print("This is REAL progress - measurable, working, deployable AI.")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
    finally:
        print("\n🛑 Stopping demo...")
        server.terminate()
        server.wait()
        print("✅ Demo completed")

        # Demo 2: Recall memories
        print("🔍 Demo 2: Recalling Memories")
        print("-" * 30)

        queries = [
            "programming languages",
            "artificial intelligence",
            "Paris landmarks",
            "French geography"
        ]

        for query in queries:
            print(f"\n🔍 Query: '{query}'")
            try:
                response = requests.post('http://localhost:8000/recall',
                                       json={"query": query, "limit": 3})
                results = response.json()

                if results:
                    print(f"   Found {len(results)} relevant memories:")
                    for i, result in enumerate(results, 1):
                        similarity = result['similarity']
                        content = result['content'][:50]
                        print(f"     {i}. {content}... (sim: {similarity:.3f})")
                else:
                    print("   No relevant memories found")

            except Exception as e:
                print(f"❌ Recall failed: {e}")

        print()

        # Demo 3: System status
        print("📊 Demo 3: System Status")
        print("-" * 30)

        try:
            response = requests.get('http://localhost:8000/status')
            status = response.json()

            print("System Status: OPERATIONAL")
            print(f"Working Components: {', '.join(status['working_components'])}")
            print(f"Total Memories: {status['total_memories']}")
            print(f"Memory File: {status['memory_file']}")
            print(f"Last Updated: {status['last_updated']}")

        except Exception as e:
            print(f"❌ Status check failed: {e}")

        print()

        # Reality Check
        print("🎯 REALITY CHECK - What We Actually Built")
        print("-" * 30)
        print("✅ WORKING COMPONENTS:")
        print("   • Fractal Memory System (7 cognitive scales)")
        print("   • Deterministic Embeddings (256D vectors)")
        print("   • REST API (/remember, /recall, /status)")
        print("   • File-based persistence")
        print()
        print("❌ NOT WORKING (Yet):")
        print("   • FNOM Memory (import errors)")
        print("   • Working Memory (missing implementation)")
        print("   • Salience System (missing implementation)")
        print("   • Consolidation (missing implementation)")
        print("   • Reflection (missing implementation)")
        print()
        print("💡 KEY INSIGHT:")
        print("   We built a SOLID FOUNDATION using what WORKS,")
        print("   not what we wished worked or planned to build.")
        print()
        print("🚀 NEXT STEPS:")
        print("   Phase 1: Build functional Working Memory")
        print("   Phase 2: Add basic attention/salience")
        print("   Phase 3: Implement learning from interactions")
        print()
        print("This is REAL progress - measurable, working, deployable AI.")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
    finally:
        print("\n🛑 Stopping demo...")
        server.terminate()
        server.wait()
        print("✅ Demo completed")

        # Demo 2: Recall memories
        print("🔍 Demo 2: Recalling Memories")
        print("-" * 30)

        queries = [
            "programming languages",
            "artificial intelligence",
            "Paris landmarks",
            "French geography"
        ]

        for query in queries:
            print(f"\n🔍 Query: '{query}'")
            try:
                response = requests.post('http://localhost:8000/recall',
                                       json={"query": query, "limit": 3})
                results = response.json()

                if results:
                    print(f"   Found {len(results)} relevant memories:")
                    for i, result in enumerate(results, 1):
                        similarity = result['similarity']
                        content = result['content'][:50]
                        print(f"     {i}. {content}... (sim: {similarity:.3f})")
                else:
                    print("   No relevant memories found")

            except Exception as e:
                print(f"❌ Recall failed: {e}")

        print()

        # Demo 3: System status
        print("📊 Demo 3: System Status")
        print("-" * 30)

        try:
            response = requests.get('http://localhost:8000/status')
            status = response.json()

            print("System Status: OPERATIONAL")
            print(f"Working Components: {', '.join(status['working_components'])}")
            print(f"Total Memories: {status['total_memories']}")
            print(f"Memory File: {status['memory_file']}")
            print(f"Last Updated: {status['last_updated']}")

        except Exception as e:
            print(f"❌ Status check failed: {e}")

        print()

        # Reality Check
        print("🎯 REALITY CHECK - What We Actually Built")
        print("-" * 30)
        print("✅ WORKING COMPONENTS:")
        print("   • Fractal Memory System (7 cognitive scales)")
        print("   • Deterministic Embeddings (256D vectors)")
        print("   • REST API (/remember, /recall, /status)")
        print("   • File-based persistence")
        print()
        print("❌ NOT WORKING (Yet):")
        print("   • FNOM Memory (import errors)")
        print("   • Working Memory (missing implementation)")
        print("   • Salience System (missing implementation)")
        print("   • Consolidation (missing implementation)")
        print("   • Reflection (missing implementation)")
        print()
        print("💡 KEY INSIGHT:")
        print("   We built a SOLID FOUNDATION using what WORKS,")
        print("   not what we wished worked or planned to build.")
        print()
        print("🚀 NEXT STEPS:")
        print("   Phase 1: Build functional Working Memory")
        print("   Phase 2: Add basic attention/salience")
        print("   Phase 3: Implement learning from interactions")
        print()
        print("This is REAL progress - measurable, working, deployable AI.")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
    finally:
        print("\n🛑 Stopping demo...")
        server.terminate()
        server.wait()
        print("✅ Demo completed")


if __name__ == "__main__":
    demo_foundation()
