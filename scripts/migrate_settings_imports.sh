#!/bin/bash
# Batch replacement script for common.config.settings → django.conf.settings
# This script updates all 142+ imports to use Django settings

set -e

cd "$(dirname "$0")/.."

echo "=== Replacing common.config.settings imports with django.conf.settings ==="

# Pattern 1: from common.config.settings import settings
find somabrain tests common observability scripts config benchmarks migrations clients -name "*.py" -type f 2>/dev/null | while read file; do
    if grep -q "from common.config.settings import settings" "$file"; then
        echo "Updating: $file (pattern 1: import settings)"
        sed -i '' 's/from common\.config\.settings import settings/from django.conf import settings/g' "$file"
    fi
done

# Pattern 2: from common.config.settings import Settings
find somabrain tests common observability scripts config benchmarks migrations clients -name "*.py" -type f 2>/dev/null | while read file; do
    if grep -q "from common.config.settings import Settings" "$file"; then
        echo "Updating: $file (pattern 2: import Settings)"
        # Replace Settings class with settings singleton from Django
        sed -i '' 's/from common\.config\.settings import Settings/from django.conf import settings/g' "$file"
        # Update Settings usage to settings in code
        sed -i '' 's/Settings(/settings\./g' "$file"
    fi
done

# Pattern 3: from common.config.settings import settings as _something
find somabrain tests common observability scripts config benchmarks migrations clients -name "*.py" -type f 2>/dev/null | while read file; do
    if grep -q "from common.config.settings import settings as" "$file"; then
        echo "Updating: $file (pattern 3: aliased import)"
        sed -i '' 's/from common\.config\.settings import settings as \([a-zA-Z_][a-zA-Z0-9_]*\)/from django.conf import settings as \1/g' "$file"
    fi
done

# Pattern 4: from common.config.settings import Settings as Config
find somabrain tests common observability scripts config benchmarks migrations clients -name "*.py" -type f 2>/dev/null | while read file; do
    if grep -q "from common.config.settings import Settings as Config" "$file"; then
        echo "Updating: $file (pattern 4: Settings as Config)"
        sed -i '' 's/from common\.config\.settings import Settings as Config/from django.conf import settings as Config/g' "$file"
    fi
done

echo "=== Verification: Checking for remaining common.config.settings imports ==="
remaining=$(grep -r "from common.config.settings import" somabrain tests common observability scripts config benchmarks 2>/dev/null | wc -l || echo "0")
echo "Remaining imports: $remaining"

if [ "$remaining" -gt 0 ]; then
    echo "WARNING: Some imports still remain. Manual review needed."
    grep -r "from common.config.settings import" somabrain tests common observability scripts config benchmarks 2>/dev/null || true
else
    echo "✅ SUCCESS: All common.config.settings imports replaced!"
fi

echo "=== Done ===\"
