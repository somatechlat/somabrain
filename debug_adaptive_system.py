#!/usr/bin/env python3
"""
Debug script to check if adaptive learning system is working.
"""

import sys
import os

# Add the somabrain module to the path
sys.path.insert(0, '/Users/macbookpro201916i964gb1tb/Documents/GitHub/somabrain')

try:
    print("🔍 Testing Adaptive Learning System Integration")
    print("=" * 50)
    
    # Test 1: Check if adaptive modules can be imported
    print("\n1. Testing imports...")
    try:
        from somabrain.adaptive.core import AdaptiveCore, AdaptiveParameter
        print("✅ Adaptive core module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import adaptive core: {e}")
        sys.exit(1)
    
    try:
        from somabrain.adaptive.integration import AdaptiveIntegrator
        print("✅ Adaptive integration module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import adaptive integration: {e}")
        sys.exit(1)
    
    # Test 2: Check if scoring module can import adaptive system
    print("\n2. Testing scoring module adaptive integration...")
    try:
        from somabrain.scoring import _ADAPTIVE_ENABLED, _adaptive_integrator
        print(f"   Adaptive enabled: {_ADAPTIVE_ENABLED}")
        print(f"   Adaptive integrator: {'Available' if _adaptive_integrator else 'None'}")
        
        if _ADAPTIVE_ENABLED and _adaptive_integrator:
            print("✅ Adaptive system is enabled in scoring module")
            
            # Test getting system stats
            try:
                stats = _adaptive_integrator.get_system_stats()
                print("✅ System stats retrieved successfully")
                print(f"   Stats: {stats}")
            except Exception as e:
                print(f"❌ Failed to get system stats: {e}")
                
            # Test getting adaptive scorer
            try:
                scorer = _adaptive_integrator.get_scorer()
                print("✅ Adaptive scorer retrieved successfully")
                print(f"   Scorer type: {type(scorer)}")
            except Exception as e:
                print(f"❌ Failed to get adaptive scorer: {e}")
        else:
            print("❌ Adaptive system is NOT enabled in scoring module")
            
    except ImportError as e:
        print(f"❌ Failed to import scoring module: {e}")
        sys.exit(1)
    
    # Test 3: Create a simple scorer and check its mode
    print("\n3. Testing scorer creation...")
    try:
        from somabrain.scoring import UnifiedScorer
        import numpy as np
        
        # Create a scorer
        scorer = UnifiedScorer(
            w_cosine=0.6,
            w_fd=0.25,
            w_recency=0.15,
            weight_min=0.0,
            weight_max=1.0,
            recency_tau=32.0
        )
        
        # Check scorer stats
        stats = scorer.stats()
        print("✅ Scorer created successfully")
        print(f"   Scorer mode: {stats.get('mode', 'unknown')}")
        print(f"   Adaptive enabled: {stats.get('adaptive_enabled', False)}")
        print(f"   Message: {stats.get('message', 'No message')}")
        
        # Test scoring with sample data
        query = np.random.rand(256)
        candidate = np.random.rand(256)
        score = scorer.score(query, candidate)
        print(f"✅ Sample scoring completed: {score:.6f}")
        
    except Exception as e:
        print(f"❌ Failed to test scorer creation: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("🎯 Debug Complete")
    
except Exception as e:
    print(f"❌ Debug failed with error: {e}")
    import traceback
    traceback.print_exc()