#!/bin/bash
# SomaBrain Roadmap Compliance Deployment Script
# This script ensures all roadmap features are properly enabled and configured

set -euo pipefail

echo "🚀 SomaBrain Roadmap Compliance Deployment"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if services are running
function check_services() {
    echo "🔍 Checking service health..."
    
    # Check main API
    if curl -s -f http://localhost:9696/health > /dev/null; then
        echo "${GREEN}✅ Main API (9696) is healthy${NC}"
    else
        echo "${RED}❌ Main API (9696) is not responding${NC}"
        return 1
    fi
    
    # Check memory service
    if curl -s -f http://localhost:9595/health > /dev/null; then
        echo "${GREEN}✅ Memory service (9595) is healthy${NC}"
    else
        echo "${RED}❌ Memory service (9595) is not responding${NC}"
        return 1
    fi
    
    return 0
}

# Update feature flags for roadmap compliance
function update_feature_flags() {
    echo "⚙️  Updating feature flags for roadmap compliance..."
    
    # Update feature overrides
    cat > data/feature_overrides.json << EOF
{
  "enabled": [
    "fusion_normalization",
    "consistency_checks", 
    "calibration",
    "hmm_segmentation",
    "drift_detection",
    "auto_rollback"
  ],
  "disabled": []
}
EOF

    echo "${GREEN}✅ Feature flags updated for roadmap compliance${NC}"
}

# Update runtime configuration
function update_runtime_config() {
    echo "⚙️  Updating runtime configuration..."
    
    # Ensure runtime overrides are set
    cat > data/runtime_overrides.json << EOF
{
  "integrator_alpha": 2.0,
  "integrator_alpha_min": 0.1,
  "integrator_alpha_max": 5.0,
  "integrator_target_regret": 0.15,
  "integrator_alpha_eta": 0.05,
  "integrator_enforce_conf": true,
  "drift_detection_enabled": true,
  "tau_anneal_mode": "exponential",
  "tau_anneal_rate": 0.95,
  "tau_min": 0.05
}
EOF

    echo "${GREEN}✅ Runtime configuration updated${NC}"
}

# Update tenant configurations
function update_tenant_configs() {
    echo "🏢 Updating tenant configurations..."
    
    # Ensure tenant learning configuration has proper parameters
    cat > config/learning.tenants.yaml << 'EOF'
production:
  hazard_lambda: 0.01
  hazard_vol_mult: 2.5
  min_samples: 50
  entropy_cap: 1.1
  alpha_target_regret: 0.15
  
demo:
  hazard_lambda: 0.03
  hazard_vol_mult: 3.5
  min_samples: 15
  entropy_cap: 1.1
  alpha_target_regret: 0.20

sandbox:
  hazard_lambda: 0.05
  hazard_vol_mult: 4.0
  min_samples: 10
  entropy_cap: 1.2
  alpha_target_regret: 0.25
EOF

    echo "${GREEN}✅ Tenant configuration updated${NC}"
}

# Restart services with new configuration
function restart_services() {
    echo "🔄 Restarting services with new configuration..."
    
    # Restart the cognitive services
    docker compose restart somabrain_cog
    docker compose restart somabrain_app
    
    echo "${GREEN}✅ Services restarted${NC}"
}

# Verify feature activation
function verify_features() {
    echo "✅ Verifying feature activation..."
    
    # Wait for services to be ready
    sleep 5
    
    # Check features endpoint
    if curl -s http://localhost:9696/features | grep -q "fusion_normalization.*true"; then
        echo "${GREEN}✅ Fusion normalization enabled${NC}"
    else
        echo "${YELLOW}⚠️  Fusion normalization might not be enabled${NC}"
    fi
    
    # Check metrics for calibration
    if curl -s http://localhost:9696/metrics | grep -q "calibration"; then
        echo "${GREEN}✅ Calibration metrics detected${NC}"
    else
        echo "${YELLOW}⚠️  Calibration metrics not detected${NC}"
    fi
}

# Run comprehensive verification
function run_verification() {
    echo "🔍 Running comprehensive verification..."
    
    # Make verification script executable
    chmod +x scripts/verify_roadmap_compliance.py
    
    # Run verification
    if python3 scripts/verify_roadmap_compliance.py; then
        echo "${GREEN}✅ All roadmap features verified${NC}"
    else
        echo "${RED}❌ Some roadmap features failed verification${NC}"
        return 1
    fi
}

# Display final status
function display_status() {
    echo ""
    echo "🎯 SomaBrain Roadmap Compliance Status"
    echo "======================================"
    echo ""
    echo "✅ Enabled Features:"
    echo "  • Fusion Normalization (e_norm_d = (error_d-μ_d)/(σ_d+ε))"
    echo "  • Consistency Checks (κ = 1 - JSD)"
    echo "  • Calibration Pipeline (ECE/Brier scores)"
    echo "  • HMM Segmentation (2-state HMM)"
    echo "  • Drift Detection (entropy-based)"
    echo "  • Tau Annealing (exponential/linear/step)"
    echo ""
    echo "✅ Mathematical Foundations:"
    echo "  • 2048-dimensional BHDC vectors"
    echo "  • Softmax fusion with adaptive α"
    echo "  • Normalized error weighting"
    echo "  • JSD-based consistency checks"
    echo ""
    echo "✅ Production Readiness:"
    echo "  • Avro-only strict mode"
    echo "  • Feature flags properly configured"
    echo "  • End-to-end integration verified"
    echo ""
}

# Main execution
function main() {
    echo "Starting roadmap compliance deployment..."
    
    check_services || {
        echo "${RED}❌ Services not ready - please start them first${NC}"
        exit 1
    }
    
    update_feature_flags
    update_runtime_config
    update_tenant_configs
    restart_services
    verify_features
    
    # Short delay for services to stabilize
    sleep 3
    
    run_verification
    display_status
    
    echo "${GREEN}🎉 Roadmap compliance deployment complete!${NC}"
}

# Execute main function
main "$@"