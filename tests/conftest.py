"""Pytest configuration for Smart Park Assistant."""
import pytest


@pytest.fixture(autouse=True)
def _default_legacy_control_discovery(monkeypatch):
    """Default all tests to legacy getMenu-first control discovery.

    Production defaults to the authoritative getListByPointId(isCtrl) discovery
    (``SPA_CONTROL_DISCOVERY_PRIMARY`` unset → "point_param"). Existing mocks don't
    stub that probe, so force "menu" here; tests for the authoritative path opt in
    with ``monkeypatch.setenv("SPA_CONTROL_DISCOVERY_PRIMARY", "point_param")``.
    """

    monkeypatch.setenv("SPA_CONTROL_DISCOVERY_PRIMARY", "menu")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Classify test failures as environment vs code issues and print to output."""
    outcome = yield
    report = outcome.get_result()
    if report.failed and call.excinfo:
        err_str = str(call.excinfo.value)
        env_indicators = [
            "ConnectionError",
            "ConnectionRefused",
            "Timeout",
            "FileNotFoundError",
            "ModuleNotFoundError",
            "ImportError",
        ]
        if any(indicator in err_str for indicator in env_indicators):
            failure_type = "environment"
            failure_hint = "Check environment setup, not code logic"
        else:
            failure_type = "code"
            failure_hint = "Review code logic and fix the assertion"

        report.user_properties.append(("failure_type", failure_type))
        report.user_properties.append(("failure_hint", failure_hint))

        # Append classification to report sections so it appears in pytest output
        report.sections.append(
            ("Failure Classification", f"Type: {failure_type} | Hint: {failure_hint}")
        )
