import os
import sys

# Add local directory to path to find the built module if not installed
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "../rust_core/target/release")
)

try:
    import somabrain_rs as rust

    print(f"✅ Rust module imported successfully. Exports: {dir(rust)}")

    # Check BHDCEncoder
    if hasattr(rust, "BHDCEncoder"):
        enc = rust.BHDCEncoder(100, 0.5, 42, "zero_one")
        if hasattr(enc, "random_vector"):
            print("✅ BHDCEncoder has random_vector")
        else:
            print("❌ BHDCEncoder MISSING random_vector")

    # Check Neuromodulators (state mirror; dynamics live in Python)
    if hasattr(rust, "Neuromodulators"):
        nm = rust.Neuromodulators()
        print(f"✅ Neuromodulators created: {nm.get_state()}")
        nm.set_state([0.4, 0.5, 0.0, 0.0])
        print(f"✅ Neuromodulators.set_state works: {nm.get_state()}")

except ImportError as e:
    print(f"❌ Failed to import somabrain_rs: {e}")
except Exception as e:
    print(f"❌ Verification failed: {e}")
