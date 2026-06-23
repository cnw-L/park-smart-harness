from agent_loop.runcontrol import RunControl


def test_default_not_interrupted():
    rc = RunControl()
    assert rc.interrupted is False


def test_request_interrupt_sets_flag():
    rc = RunControl()
    rc.request_interrupt()
    assert rc.interrupted is True


def test_request_interrupt_is_idempotent():
    rc = RunControl()
    rc.request_interrupt()
    rc.request_interrupt()
    assert rc.interrupted is True
