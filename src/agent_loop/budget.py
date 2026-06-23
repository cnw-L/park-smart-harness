from __future__ import annotations
from .config import LoopBudget

class BudgetTracker:
    """主/子共享同一实例 = 共享预算池。"""
    def __init__(self, budget: LoopBudget) -> None:
        self._b = budget
        self._iters = 0
        self._tokens = 0
        self._grace_used = False

    def consume(self, *, iterations: int = 0, tokens: int = 0) -> None:
        self._iters += iterations
        self._tokens += tokens

    def exhausted(self) -> bool:
        if self._iters >= self._b.max_iterations:
            return True
        if self._b.token_budget is not None and self._tokens >= self._b.token_budget:
            return True
        return False

    @property
    def grace_available(self) -> bool:
        return self.exhausted() and not self._grace_used

    def use_grace(self) -> None:
        self._grace_used = True

    def snapshot(self) -> dict:
        """Return consumed counters and grace flag for persistence/rehydration."""
        return {
            "iters": self._iters,
            "tokens": self._tokens,
            "grace_used": self._grace_used,
        }

    def restore(self, snapshot: dict) -> None:
        """Re-apply a persisted snapshot onto this tracker.

        Missing keys default to 0/False so older/partial snapshots do not crash.
        The budget limits come from the LoopBudget passed at construction;
        only the consumed-so-far state is restored from the snapshot.
        """
        self._iters = int(snapshot.get("iters", 0))
        self._tokens = int(snapshot.get("tokens", 0))
        self._grace_used = bool(snapshot.get("grace_used", False))
