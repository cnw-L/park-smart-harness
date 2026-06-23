# park-smart-harness

An agent **harness** for a smart-park (智慧园区) assistant. It does not replace the park's
backend — it *governs* an LLM that drives the backend: deciding what to do, gating side-effects,
shaping context, and keeping control safe.

The harness is three concentric rings plus a self-contained RAG fork:

| Ring | Package | Responsibility |
|------|---------|----------------|
| **内圈 Inner loop** | `src/agent_loop` | Transactional step-function loop (`gather → act → verify`). Seams: gate / control / verify / compaction / repair. Suspend-resume for human confirmation. Pluggable conversation stores (in-memory / Redis / Postgres idempotency ledger). |
| **中圈 Context** | `src/agent_context` | Per-turn **view** assembly (fixed system prompt / memory / history / knowledge / task layers). History reduction (drop-answered, trim, compaction-as-summary). The context is a *dynamic view*, not storage. |
| **工具 Tools** | `src/agent_tools` | Deny-first capability gate, thin metadata (`capability_code ⊥ is_control`), grounding against authoritative backend dictionaries, and a `propose → execute` control flow. Domains: facility / records / life / knowledge. |
| **RAG** | `src/harness_rag` | Self-contained retrieval (milvus + embedding + reranker), injected into the knowledge tool. Degrades gracefully to a Fake retriever offline. |

## Control flow (the load-bearing part)

Device control never lets the model touch the irreversible action directly:

1. `propose_control(device, param, value)` → grounds against the real device dictionary, registers a
   `ControlProposal` (read-only), returns **no handle to the model**.
2. `execute_proposal` (no arguments) → the engine freezes the *latest unresolved* proposal, the gate
   classifies it `ask`, and the loop **suspends** with a confirmation card.
3. The user confirms on the card; the engine executes + reads back to reconcile (accepted ≠ effective).

The handle round-trips through the card + confirm endpoint — **never through model text** — so a model
that mis-copies or fabricates an id cannot actuate the wrong device. Control defaults to **simulated**
(no real `deviceCtrl`) until the backend exposes `commandId`/idempotency.

## Layout

```
src/agent_loop/      inner loop engine + stores + providers
src/agent_context/   per-turn context assembler + reducers
src/agent_tools/     tool governance, grounding, control, domains
src/harness_rag/     vendored RAG (milvus retrieve + rerank)
scripts/demo_server.py   FastAPI demo wiring all four together
tests/               435 tests (offline; live infra gated behind env flags)
```

## Run

```bash
pip install -e ".[dev,storage,rag]"      # or just ".[dev]" for offline tests
cp .env.example .env                      # fill in LLM / backend / RAG endpoints

# Tests (offline — no infra needed; live variants are skipped without env flags)
pytest -q

# Demo (real qwen + real backend; control stays simulated by default)
python scripts/demo_server.py             # serves the demo UI; paste a backend token in the page
```

### Notes
- **Tokens are short-lived.** The backend (RuoYi) bearer token has a server-side TTL; when control
  calls return `认证失败`, refresh the token — it is an auth failure, not a device-name problem.
- **`HARNESS_CONTROL_EXECUTION=real`** enables real downlink; leave unset for simulated.
- **`HARNESS_RAG_LIVE=0`** forces the offline Fake retriever; otherwise the knowledge tool uses the
  real milvus collection.
