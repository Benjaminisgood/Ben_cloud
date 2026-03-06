from __future__ import annotations

from benbot_api.services.metrics import inc_counter, render_prometheus_metrics


class _DBStub:
    class _Query:
        def all(self):
            return []

        def group_by(self, *_args, **_kwargs):
            return self

        def scalar(self):
            return 0

    def query(self, *_args, **_kwargs):
        return self._Query()


def test_render_prometheus_metrics_includes_core_counters() -> None:
    inc_counter("benbot_login_failure_total")
    text = render_prometheus_metrics(_DBStub())
    assert "benbot_login_failure_total" in text
    assert "benbot_runtime_unix_timestamp" in text
