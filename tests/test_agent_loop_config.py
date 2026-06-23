from agent_loop.config import LoopBudget, LoopConfig

def test_loop_config_holds_per_layer_knobs():
    budget = LoopBudget(max_iterations=5, token_budget=1000)
    cfg = LoopConfig(model="hy3-preview", max_tokens=800, temperature=0.0,
                     role="main", toolset=["echo"], budget=budget)
    assert cfg.role == "main"
    assert cfg.toolset == ["echo"]
    assert cfg.budget.max_iterations == 5
    assert cfg.max_depth == 2
    assert budget.max_tool_failures == 3
