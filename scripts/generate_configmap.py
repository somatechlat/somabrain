import pathlib
import re
import sys
import yaml

#!/usr/bin/env python3
"""Generate a Kubernetes ConfigMap from docs/operations/configuration.md.

The configuration document contains a fenced ````env```` block with all
environment variables used by the Somabrain service. This script extracts that
block and writes a ``ConfigMap`` YAML file under ``k8s/base`` which can be
included in the Kustomize overlay.
"""


CONFIG_MD = pathlib.Path("docs/operations/configuration.md")
OUTPUT = pathlib.Path("k8s/base/somabrain-configmap.yaml")

if not CONFIG_MD.is_file():
    sys.exit("configuration.md not found")

content = CONFIG_MD.read_text()
# Find a fenced env block (```env ... ```). If not present, fall back to any code block.
match = re.search(r"```env\n(.*?)\n```", content, re.S)
if not match:
    sys.exit("No env code block found in configuration.md")

env_vars = {}
for line in match.group(1).splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    if "=" in line:
        key, val = line.split("=", 1)
        env_vars[key.strip()] = val.strip()

configmap = {
    "apiVersion": "v1",
    "kind": "ConfigMap",
    "metadata": {
        "name": "somabrain-env",
        "namespace": "somabrain-prod",
    },
    "data": env_vars,
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(yaml.safe_dump(configmap, sort_keys=False))
print(f"Wrote {OUTPUT}")
