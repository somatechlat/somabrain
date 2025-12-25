#!/bin/bash
# Batch fix ALL sleep settings attributes to UPPERCASE

set -e

echo "=== Fixing ALL sleep settings in sleep/__init__.py ==="

sed -i '' \
  -e 's/settings\.sleep_k0/settings.SLEEP_K0/g' \
  -e 's/settings\.sleep_t0/settings.SLEEP_T0/g' \
  -e 's/settings\.sleep_tau0/settings.SLEEP_TAU0/g' \
  -e 's/settings\.sleep_eta0/settings.SLEEP_ETA0/g' \
  -e 's/settings\.sleep_lambda0/settings.SLEEP_LAMBDA0/g' \
  -e 's/settings\.sleep_B0/settings.SLEEP_B0/g' \
  -e 's/settings\.sleep_K_min/settings.SLEEP_K_MIN/g' \
  -e 's/settings\.sleep_t_min/settings.SLEEP_T_MIN/g' \
  -e 's/settings\.sleep_alpha_K/settings.SLEEP_ALPHA_K/g' \
  -e 's/settings\.sleep_alpha_t/settings.SLEEP_ALPHA_T/g' \
  somabrain/sleep/__init__.py

echo "✅ All sleep settings fixed"

# Also fix any in sleep routers
for file in somabrain/sleep/*_router.py; do
  if [ -f "$file" ]; then
    echo "Checking $file..."
    sed -i '' \
      -e 's/settings\.sleep_/settings.SLEEP_/g' \
      "$file"
  fi
done

echo "✅ Complete - all sleep settings are now UPPERCASE"
