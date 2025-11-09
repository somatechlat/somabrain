from typing import Any

# Expose minimal top-level symbols used in the repo
metrics: Any
trace: Any

def get_tracer(name: str) -> Any: ...

class Tracer: ...
