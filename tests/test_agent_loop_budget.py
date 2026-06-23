from agent_loop.budget import BudgetTracker
from agent_loop.config import LoopBudget

def test_iteration_exhaustion_then_one_grace():
    t = BudgetTracker(LoopBudget(max_iterations=2))
    t.consume(iterations=1); assert not t.exhausted()
    t.consume(iterations=1); assert t.exhausted()
    assert t.grace_available is True
    t.use_grace(); assert t.grace_available is False

def test_token_exhaustion():
    # interrupt 已移至 RunControl(S1);此处只保留 token 耗尽断言
    t = BudgetTracker(LoopBudget(max_iterations=99, token_budget=100))
    t.consume(tokens=100)
    assert t.exhausted()

# --- snapshot / restore ---

def test_snapshot_restore_preserves_exhausted_state():
    """Consume until exhausted, snapshot, restore onto a fresh tracker, verify same state."""
    budget = LoopBudget(max_iterations=3)
    original = BudgetTracker(budget)
    original.consume(iterations=3)
    assert original.exhausted()

    snap = original.snapshot()

    fresh = BudgetTracker(budget)
    assert not fresh.exhausted()  # sanity: fresh tracker is NOT exhausted

    fresh.restore(snap)
    assert fresh.exhausted()  # after restore it must be exhausted again

def test_snapshot_restore_preserves_partial_counters():
    """Partial consumption: remaining budget identical after restore."""
    budget = LoopBudget(max_iterations=10, token_budget=500)
    original = BudgetTracker(budget)
    original.consume(iterations=4, tokens=200)
    assert not original.exhausted()

    snap = original.snapshot()
    assert snap == {"iters": 4, "tokens": 200, "grace_used": False}

    restored = BudgetTracker(budget)
    restored.restore(snap)
    assert not restored.exhausted()
    # One more iteration that would push original over — same for restored
    restored.consume(iterations=6)
    assert restored.exhausted()

def test_snapshot_restore_grace_used_roundtrip():
    """grace_used flag survives snapshot/restore correctly."""
    budget = LoopBudget(max_iterations=1)
    t = BudgetTracker(budget)
    t.consume(iterations=1)
    assert t.grace_available is True
    t.use_grace()
    assert t.grace_available is False

    snap = t.snapshot()
    assert snap["grace_used"] is True

    restored = BudgetTracker(budget)
    restored.restore(snap)
    # Grace was already used — must not be available again
    assert restored.grace_available is False

def test_restore_empty_snapshot_does_not_crash():
    """restore({}) must not raise and must yield a fresh-equivalent tracker."""
    budget = LoopBudget(max_iterations=5, token_budget=100)
    t = BudgetTracker(budget)
    t.restore({})  # partial / empty snapshot — must not crash
    assert not t.exhausted()
    assert t.grace_available is False  # not exhausted yet, so grace not available

def test_restore_partial_snapshot_defaults_missing_keys():
    """A snapshot with only some keys (e.g., older format) must not crash."""
    budget = LoopBudget(max_iterations=5)
    t = BudgetTracker(budget)
    t.restore({"iters": 3})  # tokens and grace_used missing
    assert not t.exhausted()  # 3 < 5
    t.consume(iterations=2)
    assert t.exhausted()

def test_no_deadline_s_on_loop_budget():
    """LoopBudget must NOT have a deadline_s field (wall-clock removed)."""
    assert not hasattr(LoopBudget(max_iterations=1), "deadline_s")
