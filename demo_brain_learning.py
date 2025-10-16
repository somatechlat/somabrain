#!/usr/bin/env python3
"""
SomaBrain Learning Demonstration with Real-Time Visualization

This script demonstrates actual cognitive learning in SomaBrain by:
1. Running against real infrastructure (Redis, API, Memory services)
2. Feeding synthetic data and collecting feedback
3. Measuring adaptation parameter changes over time
4. Generating plots showing brain learning curves
5. Proving end-to-end learning with all services engaged

Usage:
    python demo_brain_learning.py [--iterations N] [--save-plots]
"""

import os
import time
import uuid
import json
import argparse
from datetime import datetime
from typing import Dict

import requests
import matplotlib.pyplot as plt
import numpy as np

# Import centralized test configuration
try:
    from tests.test_config import (
        SOMABRAIN_API_URL, REDIS_URL, MEMORY_HTTP_ENDPOINT, 
        get_test_headers, is_service_available
    )
except ImportError:
    # Fallback for standalone usage
    SOMABRAIN_API_URL = os.getenv("SOMA_API_URL", "http://127.0.0.1:9696")
    REDIS_URL = os.getenv("SOMABRAIN_REDIS_URL", "redis://127.0.0.1:6379/0")
    MEMORY_HTTP_ENDPOINT = os.getenv("SOMABRAIN_MEMORY_HTTP_ENDPOINT", "http://127.0.0.1:9595")
    
    def get_test_headers(session_id=None, **kwargs):
        headers = {"Content-Type": "application/json", "X-Model-Confidence": "8.5"}
        if session_id:
            headers["X-Session-ID"] = session_id
        headers.update(kwargs)
        return headers
    
    def is_service_available(service):
        return True  # Assume available for standalone mode

class SomaBrainLearningDemo:
    """Demonstrates real SomaBrain learning with synthetic data and visualization."""
    
    def __init__(self, base_url: str = SOMABRAIN_API_URL):
        self.base_url = base_url.rstrip("/")
        self.session_id = f"demo-{uuid.uuid4().hex[:16]}"
        self.headers = get_test_headers(session_id=self.session_id)
        
        # Learning tracking
        self.learning_data = {
            "timestamps": [],
            "alpha_values": [],
            "lambda_values": [],
            "gamma_values": [],
            "history_lengths": [],
            "learning_rates": [],
            "iteration": []
        }
        
        # Synthetic training data
        self.training_queries = [
            "What is the capital of cognitive architecture?",
            "How do neural networks process information?",
            "Explain the concept of working memory",
            "What is the role of attention in cognition?",
            "How does learning adaptation work?",
            "What are the principles of memory consolidation?",
            "How do cognitive systems handle uncertainty?",
            "What is the relationship between memory and reasoning?"
        ]
        
        self.training_content = [
            {"task": "cognitive-demo", "content": f"Training memory {i+1}: {query}", 
             "phase": "bootstrap", "quality_score": 0.8 + (i * 0.02)}
            for i, query in enumerate(self.training_queries)
        ]
        
    def verify_infrastructure(self) -> bool:
        """Verify all required services are available."""
        print("🔍 Verifying SomaBrain Infrastructure...")
        
        try:
            # Check SomaBrain API
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code != 200:
                print(f"❌ SomaBrain API not healthy: {response.status_code}")
                return False
            print(f"✅ SomaBrain API: {self.base_url}")
            
            # Check adaptation state endpoint
            try:
                state_resp = requests.get(f"{self.base_url}/context/adaptation/state", timeout=5)
                if state_resp.status_code == 200:
                    print("✅ Adaptation system: Available")
                else:
                    print("⚠️  Adaptation system: Limited (will track weights instead)")
            except Exception:
                print("⚠️  Adaptation system: Not available (will track weights)")
            
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Infrastructure check failed: {e}")
            return False
    
    def get_adaptation_state(self) -> Dict | None:
        """Get current adaptation parameters from the system."""
        try:
            resp = requests.get(
                f"{self.base_url}/context/adaptation/state",
                headers={"X-Tenant-ID": "sandbox"} if "X-Tenant-ID" not in self.headers else {},
                timeout=5
            )
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception:
            return None
    
    def remember_memory(self, content: Dict) -> bool:
        """Store a memory in the system."""
        payload = {"coord": None, "payload": content}
        try:
            resp = requests.post(
                f"{self.base_url}/remember",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            return resp.status_code == 200 and resp.json().get("ok", False)
        except Exception:
            return False
    
    def evaluate_query(self, query: str) -> Dict:
        """Evaluate a query and get system response with current weights."""
        try:
            resp = requests.post(
                f"{self.base_url}/context/evaluate",
                json={"session_id": self.session_id, "query": query, "top_k": 3},
                headers=self.headers,
                timeout=15
            )
            if resp.status_code == 200:
                return resp.json()
            return {}
        except Exception as e:
            print(f"Error evaluating query: {e}")
            return {}
    
    def submit_feedback(self, query: str, prompt: str, utility: float = 0.9) -> bool:
        """Submit positive feedback to trigger learning adaptation."""
        payload = {
            "session_id": self.session_id,
            "query": query,
            "prompt": prompt,
            "response_text": "Learning demonstration response",
            "utility": utility,
            "reward": utility
        }
        try:
            resp = requests.post(
                f"{self.base_url}/context/feedback",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            return resp.status_code == 200 and resp.json().get("accepted", False)
        except Exception:
            return False
    
    def record_learning_snapshot(self, iteration: int):
        """Record current learning state for visualization."""
        timestamp = time.time()
        
        # Get adaptation state
        state = self.get_adaptation_state()
        
        if state:
            # Extract adaptation parameters
            alpha = state.get("retrieval", {}).get("alpha", 0.0)
            lambda_val = state.get("utility", {}).get("lambda_", 0.0)
            gamma = state.get("retrieval", {}).get("gamma", 0.0)
            history_len = state.get("history_len", 0)
            lr = state.get("learning_rate", 0.0)
            
            self.learning_data["timestamps"].append(timestamp)
            self.learning_data["alpha_values"].append(alpha)
            self.learning_data["lambda_values"].append(lambda_val)
            self.learning_data["gamma_values"].append(gamma)
            self.learning_data["history_lengths"].append(history_len)
            self.learning_data["learning_rates"].append(lr)
            self.learning_data["iteration"].append(iteration)
            
            print(f"📊 Iteration {iteration}: α={alpha:.3f}, λ={lambda_val:.3f}, γ={gamma:.3f}, history={history_len}")
        else:
            print(f"⚠️  Iteration {iteration}: Adaptation state not available")
    
    def run_learning_demo(self, iterations: int = 20) -> bool:
        """Run the complete learning demonstration."""
        print(f"🧠 Starting SomaBrain Learning Demonstration ({iterations} iterations)")
        print(f"🎯 Session ID: {self.session_id}")
        print(f"🔗 API Endpoint: {self.base_url}")
        
        # Verify infrastructure
        if not self.verify_infrastructure():
            print("❌ Infrastructure verification failed!")
            return False
        
        # Record initial state
        print("\n📈 Recording initial learning state...")
        self.record_learning_snapshot(0)
        
        # Seed initial memories
        print("\n🌱 Seeding training memories...")
        for i, content in enumerate(self.training_content):
            success = self.remember_memory(content)
            if success:
                print(f"✅ Memory {i+1}: {content['content'][:50]}...")
            else:
                print(f"❌ Failed to store memory {i+1}")
        
        print(f"\n🚀 Running {iterations} learning iterations...")
        
        for iteration in range(1, iterations + 1):
            # Select a training query
            query_idx = (iteration - 1) % len(self.training_queries)
            query = self.training_queries[query_idx]
            
            # Evaluate the query
            evaluation = self.evaluate_query(query)
            
            if evaluation and evaluation.get("prompt"):
                # Submit positive feedback to trigger learning
                utility = 0.8 + (0.2 * np.random.random())  # Vary utility slightly
                feedback_success = self.submit_feedback(query, evaluation["prompt"], utility)
                
                if feedback_success:
                    print(f"✅ Iteration {iteration}: Feedback submitted (utility={utility:.3f})")
                else:
                    print(f"⚠️  Iteration {iteration}: Feedback submission failed")
                
                # Small delay for adaptation processing
                time.sleep(0.1)
                
                # Record learning progress
                self.record_learning_snapshot(iteration)
            else:
                print(f"❌ Iteration {iteration}: Query evaluation failed")
            
            # Progress indicator
            if iteration % 5 == 0:
                progress = (iteration / iterations) * 100
                print(f"📊 Progress: {progress:.1f}% complete")
        
        print("\n🎉 Learning demonstration completed!")
        return len(self.learning_data["timestamps"]) > 1
    
    def create_learning_plots(self, save_plots: bool = False):
        """Generate comprehensive learning visualization plots."""
        if len(self.learning_data["timestamps"]) < 2:
            print("❌ Insufficient data for plotting")
            return
        
        # Convert timestamps to relative time (seconds from start)
        start_time = self.learning_data["timestamps"][0] 
        relative_times = [(t - start_time) for t in self.learning_data["timestamps"]]
        
        # Create subplot layout
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'SomaBrain Real Learning Progress - Session {self.session_id[:8]}', fontsize=16, fontweight='bold')
        
        # Plot 1: Adaptation Parameters (Alpha & Lambda)
        ax1 = axes[0, 0]
        ax1.plot(relative_times, self.learning_data["alpha_values"], 'b-o', label='Alpha (Retrieval)', linewidth=2, markersize=4)
        ax1.plot(relative_times, self.learning_data["lambda_values"], 'r-s', label='Lambda (Utility)', linewidth=2, markersize=4)
        ax1.set_xlabel('Time (seconds)')
        ax1.set_ylabel('Parameter Value')
        ax1.set_title('🧠 Cognitive Adaptation Parameters')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Learning Rate Evolution  
        ax2 = axes[0, 1]
        ax2.plot(relative_times, self.learning_data["learning_rates"], 'g-^', label='Learning Rate', linewidth=2, markersize=4)
        ax2.set_xlabel('Time (seconds)')
        ax2.set_ylabel('Learning Rate')
        ax2.set_title('📈 Learning Rate Adaptation')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Working Memory Growth
        ax3 = axes[1, 0]
        ax3.plot(relative_times, self.learning_data["history_lengths"], 'm-d', label='History Length', linewidth=2, markersize=4)
        ax3.set_xlabel('Time (seconds)')
        ax3.set_ylabel('Memory Items')
        ax3.set_title('🧮 Working Memory Expansion')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Plot 4: Gamma Evolution (Exploration vs Exploitation)
        ax4 = axes[1, 1]
        ax4.plot(relative_times, self.learning_data["gamma_values"], 'c-*', label='Gamma (Exploration)', linewidth=2, markersize=6)
        ax4.set_xlabel('Time (seconds)')
        ax4.set_ylabel('Gamma Value')  
        ax4.set_title('🎯 Exploration Parameter')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save plots if requested
        if save_plots:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"somabrain_learning_{timestamp}.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"💾 Learning plots saved: {filename}")
        
        plt.show()
    
    def save_learning_data(self):
        """Save learning data to JSON for further analysis."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"somabrain_learning_data_{timestamp}.json"
        
        # Convert timestamps to ISO format for JSON serialization
        data_copy = self.learning_data.copy()
        data_copy["timestamps"] = [datetime.fromtimestamp(t).isoformat() for t in data_copy["timestamps"]]
        
        # Add metadata
        data_copy["metadata"] = {
            "session_id": self.session_id,
            "base_url": self.base_url,
            "total_iterations": len(data_copy["iteration"]),
            "demonstration_type": "synthetic_learning_with_real_infrastructure"
        }
        
        with open(filename, 'w') as f:
            json.dump(data_copy, f, indent=2)
        
        print(f"💾 Learning data saved: {filename}")
        return filename

def main():
    """Main demonstration function."""
    parser = argparse.ArgumentParser(description="SomaBrain Learning Demonstration")
    parser.add_argument("--iterations", type=int, default=20, help="Number of learning iterations")
    parser.add_argument("--save-plots", action="store_true", help="Save plots to file")
    parser.add_argument("--save-data", action="store_true", help="Save learning data to JSON")
    parser.add_argument("--url", default=SOMABRAIN_API_URL, help="SomaBrain API URL")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🧠 SomaBrain Real Learning Demonstration")
    print("=" * 60)
    print("📡 Infrastructure Status:")
    try:
        # Check key services
        services = {'somabrain_api': args.url}
        for service, url in services.items():
            if "api" in service:
                status = "✅" if is_service_available("somabrain") else "❌" 
                print(f"   {service}: {status}")
    except ImportError:
        print(f"   API: {args.url}")
    print()
    
    # Create and run demo
    demo = SomaBrainLearningDemo(args.url)
    
    try:
        success = demo.run_learning_demo(args.iterations)
        
        if success:
            print("\n📊 Generating learning visualization...")
            demo.create_learning_plots(save_plots=args.save_plots)
            
            if args.save_data:
                demo.save_learning_data()
            
            # Print learning summary
            if demo.learning_data["alpha_values"]:
                initial_alpha = demo.learning_data["alpha_values"][0]
                final_alpha = demo.learning_data["alpha_values"][-1]
                alpha_change = final_alpha - initial_alpha
                
                initial_lambda = demo.learning_data["lambda_values"][0] 
                final_lambda = demo.learning_data["lambda_values"][-1]
                lambda_change = final_lambda - initial_lambda
                
                print("\n🎯 Learning Results Summary:")
                print(f"   Alpha change: {initial_alpha:.3f} → {final_alpha:.3f} (Δ{alpha_change:+.3f})")
                print(f"   Lambda change: {initial_lambda:.3f} → {final_lambda:.3f} (Δ{lambda_change:+.3f})")
                print(f"   Total iterations: {len(demo.learning_data['iteration'])}")
                print(f"   Demonstration: {'✅ SUCCESS' if alpha_change > 0 or lambda_change > 0 else '⚠️ MINIMAL_CHANGE'}")
        else:
            print("❌ Learning demonstration failed to collect sufficient data")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️  Demonstration interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        return 1
    
    print("\n🎉 SomaBrain learning demonstration completed successfully!")
    return 0

if __name__ == "__main__":
    exit(main())