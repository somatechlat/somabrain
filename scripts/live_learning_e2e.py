"""Live E2E proof that agent interactions train the brain.

Runs against the running stack (default ``http://127.0.0.1:30101``) and
asserts that feedback moves AdaptationEngine weights.

Credential law (VIBE Rule 164 / Art 26):
  * The API bearer is resolved through the Vault token *file path*.
  * Secret values are never read from the process environment.
  * Topology (paths, URLs, ports) may come from the environment.

Sequence:
  1. ``GET  /context/adaptation/state``  (before)
  2. ``POST /memory/remember``           (best-effort; recorded)
  3. ``POST /memory/recall``             (memory event; must MOVE weights)
  4. ``POST /context/feedback``          (N times; each must report
                                          ``adaptation_applied``)
  5. ``GET  /context/adaptation/state``  (after)

Assertions:
  * memory events (recall hit/miss, and store when it succeeds) MOVE
    ``retrieval.alpha`` / ``utility.lambda_`` (APM-1 shared engine)
  * every feedback response has ``adaptation_applied is True``
  * ``retrieval.alpha`` and ``utility.lambda_`` both MOVE under feedback
  * ``history_len`` increases

Exit codes: 0 = proven, 1 = assertion failure, 2 = stack/token unavailable.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# --- topology (env-allowed) -----------------------------------------------
DEFAULT_API = "http://127.0.0.1:30101"
DEFAULT_VAULT = "http://127.0.0.1:30200"
FEEDBACK_ROUNDS = 8
FEEDBACK_UTILITY = 0.95
FEEDBACK_REWARD = 0.95

# Secret-file names inside the t0 secrets directory (filenames are topology).
VAULT_ROOT_TOKEN_NAME = "brain_vault_root_token"
MEMORY_HTTP_TOKEN_NAME = "somabrain_memory_http_token"

# Vault KV path/key for the shared agent bearer (vault_client.SHARED_*).
SHARED_CREDENTIALS_PATH = "secret/data/agent/credentials"
MEMORY_HTTP_TOKEN_KEY = "somabrain_memory_http_token"


@dataclass(frozen=True)
class Evidence:
    """One observed fact from the live run."""

    step: str
    detail: dict[str, Any]


@dataclass
class ProofResult:
    """Outcome of a live learning proof run."""

    ok: bool
    evidence: list[Evidence] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def add(self, step: str, detail: dict[str, Any]) -> None:
        self.evidence.append(Evidence(step=step, detail=detail))

    def fail(self, message: str) -> None:
        self.ok = False
        self.failures.append(message)


# --- token resolution (file paths only) -----------------------------------


def _secrets_dir() -> Path:
    """Return the t0 secrets directory named by topology env paths.

    ``SOMA_T0_SECRETS_DIR`` and ``VAULT_TOKEN_FILE`` are *paths* (topology).
    Never treat their contents as environment secrets.
    """
    direct = os.environ.get("SOMA_T0_SECRETS_DIR", "").strip()
    if direct:
        return Path(direct)
    token_file = os.environ.get("VAULT_TOKEN_FILE", "").strip()
    if token_file:
        return Path(token_file).parent
    # Well-known standalone layout used by infra/standalone/.env.
    candidate = (
        Path(__file__).resolve().parents[2]
        / "somaAgent01"
        / "infra"
        / "standalone"
        / "secrets"
    )
    if candidate.is_dir():
        return candidate
    raise FileNotFoundError(
        "cannot resolve t0 secrets directory: set SOMA_T0_SECRETS_DIR or "
        "VAULT_TOKEN_FILE to a path (topology). Secret values must never "
        "come from the environment."
    )


def _read_secret_file(name: str) -> str:
    """Read a secret value from a named file under the secrets directory."""
    path = _secrets_dir() / name
    if not path.is_file() or path.stat().st_size == 0:
        raise FileNotFoundError(f"secret file missing or empty: {path}")
    return path.read_text(encoding="utf-8").strip()


def _vault_addr() -> str:
    return (
        os.environ.get("SOMABRAIN_VAULT_ADDR", DEFAULT_VAULT).strip() or DEFAULT_VAULT
    )


def resolve_bearer_token() -> str:
    """Return the API bearer via Vault lookup on the token-file path.

    Preferred: Vault root token from ``brain_vault_root_token`` (file) ->
    ``GET secret/data/agent/credentials`` -> ``somabrain_memory_http_token``.
    Fallback: the same key's file under the secrets directory (still a file
    path, never an environment secret).
    """
    vault_token = _read_secret_file(VAULT_ROOT_TOKEN_NAME)
    url = f"{_vault_addr().rstrip('/')}/v1/{SHARED_CREDENTIALS_PATH}"
    request = urllib.request.Request(url, headers={"X-Vault-Token": vault_token})
    try:
        with urllib.request.urlopen(request, timeout=8) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        token = (
            body.get("data", {}).get("data", {}).get(MEMORY_HTTP_TOKEN_KEY) or ""
        ).strip()
        if token:
            return token
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        pass
    # File fallback: same trust boundary, still path-only.
    return _read_secret_file(MEMORY_HTTP_TOKEN_NAME)


# --- HTTP helpers ----------------------------------------------------------


@dataclass(frozen=True)
class HttpResult:
    status: int
    body: Any


def _call(
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 20.0,
) -> HttpResult:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read()
            try:
                return HttpResult(resp.status, json.loads(raw or b"{}"))
            except json.JSONDecodeError:
                return HttpResult(resp.status, raw.decode("utf-8", "replace")[:500])
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return HttpResult(exc.code, json.loads(raw or b"{}"))
        except json.JSONDecodeError:
            return HttpResult(exc.code, raw.decode("utf-8", "replace")[:500])
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return HttpResult(0, {"error": f"{type(exc).__name__}: {exc}"})


def _api_base() -> str:
    return (
        os.environ.get("SOMABRAIN_API_URL", DEFAULT_API).strip().rstrip("/")
        or DEFAULT_API
    )


# --- proof -----------------------------------------------------------------


def _weights(state: dict[str, Any]) -> tuple[float, float, int]:
    retrieval = state.get("retrieval") or {}
    utility = state.get("utility") or {}
    alpha = float(retrieval.get("alpha"))
    lambda_ = float(utility.get("lambda_"))
    history = int(state.get("history_len") or 0)
    return alpha, lambda_, history


def run_proof() -> ProofResult:
    """Execute the live learning proof and return structured evidence."""
    result = ProofResult(ok=True)
    base = _api_base()

    try:
        token = resolve_bearer_token()
    except FileNotFoundError as exc:
        result.fail(f"token path unavailable: {exc}")
        result.add("token", {"error": str(exc)})
        return result

    result.add("token", {"source": "vault-or-file-path", "api": base})

    # 1) adaptation state BEFORE
    before = _call("GET", f"{base}/context/adaptation/state", token)
    if before.status != 200 or not isinstance(before.body, dict):
        result.fail(
            f"adaptation state BEFORE unavailable: {before.status} {before.body}"
        )
        result.add("state_before", {"status": before.status, "body": before.body})
        return result
    alpha0, lambda0, hist0 = _weights(before.body)
    result.add(
        "state_before",
        {"alpha": alpha0, "lambda_": lambda0, "history_len": hist0, "raw": before.body},
    )

    # 2) remember (best-effort — SFM may reject; recorded, not hard-asserted)
    ts = int(time.time())
    text = f"live_learning_e2e memory {ts}"
    key = f"live-e2e-{ts}"
    remember_body = {
        "namespace": "wm",
        "key": key,
        "value": {"text": text, "kind": "episodic"},
        "text": text,
        "kind": "episodic",
        "source": "live_learning_e2e",
    }
    remember = _call("POST", f"{base}/memory/remember", token, remember_body)
    result.add(
        "remember",
        {
            "status": remember.status,
            "ok": isinstance(remember.body, dict)
            and (
                remember.body.get("ok") is True
                or remember.body.get("durability") is not None
            ),
            "body": remember.body,
        },
    )

    # 2b) memory-event learning: recall is an APM-1 teacher signal and MUST
    #     move the same weights that /context/adaptation/state reports.
    mem_before = _call("GET", f"{base}/context/adaptation/state", token)
    if mem_before.status != 200 or not isinstance(mem_before.body, dict):
        result.fail(f"adaptation state pre-recall unavailable: {mem_before.status}")
        result.add(
            "state_pre_recall", {"status": mem_before.status, "body": mem_before.body}
        )
        return result
    m_alpha0, m_lambda0, m_hist0 = _weights(mem_before.body)

    recall = _call(
        "POST",
        f"{base}/memory/recall",
        token,
        {"query": text, "namespace": "wm", "top_k": 5},
    )
    result.add(
        "recall",
        {
            "status": recall.status,
            "hits": (
                len(recall.body.get("results") or [])
                if isinstance(recall.body, dict)
                else None
            ),
            "body": (
                {
                    k: recall.body.get(k)
                    for k in ("tenant", "namespace", "wm_hits", "ltm_hits")
                }
                if isinstance(recall.body, dict)
                else recall.body
            ),
        },
    )

    mem_after = _call("GET", f"{base}/context/adaptation/state", token)
    if mem_after.status != 200 or not isinstance(mem_after.body, dict):
        result.fail(f"adaptation state post-recall unavailable: {mem_after.status}")
        result.add(
            "state_post_recall", {"status": mem_after.status, "body": mem_after.body}
        )
        return result
    m_alpha1, m_lambda1, m_hist1 = _weights(mem_after.body)
    result.add(
        "state_post_recall",
        {"alpha": m_alpha1, "lambda_": m_lambda1, "history_len": m_hist1},
    )
    if m_alpha1 == m_alpha0 and m_lambda1 == m_lambda0:
        result.fail(
            "memory events did NOT move weights "
            f"(alpha {m_alpha0}->{m_alpha1}, lambda_ {m_lambda0}->{m_lambda1})"
        )
    if m_hist1 <= m_hist0:
        result.fail(
            f"history_len did not increase on memory events ({m_hist0} -> {m_hist1})"
        )
    result.add(
        "delta_memory_events",
        {
            "alpha": f"{m_alpha0} -> {m_alpha1}",
            "lambda_": f"{m_lambda0} -> {m_lambda1}",
            "history_len": f"{m_hist0} -> {m_hist1}",
        },
    )

    # 3) feedback rounds — agent interaction that must train the brain
    applied_count = 0
    for round_index in range(FEEDBACK_ROUNDS):
        feedback = _call(
            "POST",
            f"{base}/context/feedback",
            token,
            {"utility": FEEDBACK_UTILITY, "reward": FEEDBACK_REWARD},
        )
        body = feedback.body if isinstance(feedback.body, dict) else {}
        applied = body.get("adaptation_applied")
        result.add(
            f"feedback_{round_index}",
            {
                "status": feedback.status,
                "adaptation_applied": applied,
                "utility": FEEDBACK_UTILITY,
                "reward": FEEDBACK_REWARD,
            },
        )
        if feedback.status != 200:
            result.fail(f"feedback {round_index} HTTP {feedback.status}: {body}")
            continue
        if applied is not True:
            result.fail(
                f"feedback {round_index} adaptation_applied is not True: {applied!r}"
            )
            continue
        applied_count += 1

    if applied_count != FEEDBACK_ROUNDS:
        result.fail(f"only {applied_count}/{FEEDBACK_ROUNDS} feedback rounds applied")

    # 4) adaptation state AFTER
    after = _call("GET", f"{base}/context/adaptation/state", token)
    if after.status != 200 or not isinstance(after.body, dict):
        result.fail(f"adaptation state AFTER unavailable: {after.status} {after.body}")
        result.add("state_after", {"status": after.status, "body": after.body})
        return result
    alpha1, lambda1, hist1 = _weights(after.body)
    result.add(
        "state_after",
        {"alpha": alpha1, "lambda_": lambda1, "history_len": hist1, "raw": after.body},
    )

    # --- hard assertions ---------------------------------------------------
    if alpha1 == alpha0:
        result.fail(f"alpha did not MOVE (stuck at {alpha0!r})")
    if lambda1 == lambda0:
        result.fail(f"lambda_ did not MOVE (stuck at {lambda0!r})")
    if hist1 <= hist0:
        result.fail(f"history_len did not increase ({hist0} -> {hist1})")

    result.add(
        "delta",
        {
            "alpha": f"{alpha0} -> {alpha1}",
            "lambda_": f"{lambda0} -> {lambda1}",
            "history_len": f"{hist0} -> {hist1}",
        },
    )
    return result


def format_evidence(result: ProofResult) -> str:
    """Render the evidence table for operators."""
    lines = [
        "| step | detail |",
        "|---|---|",
    ]
    for item in result.evidence:
        detail = json.dumps(item.detail, sort_keys=True, default=str)
        if len(detail) > 160:
            detail = detail[:157] + "..."
        lines.append(f"| {item.step} | {detail} |")
    lines.append("")
    lines.append(f"RESULT: {'PROVEN' if result.ok else 'FAILED'}")
    for failure in result.failures:
        lines.append(f"FAIL: {failure}")
    return "\n".join(lines)


def main() -> int:
    result = run_proof()
    print(format_evidence(result))
    if not result.ok:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
