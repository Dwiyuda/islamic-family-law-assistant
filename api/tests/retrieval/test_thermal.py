import pytest

from app.retrieval import thermal
from app.retrieval.thermal import wait_until_cool


def test_off_when_max_temp_zero():
    assert wait_until_cool(0, 68, read=lambda: 90, sleep=lambda s: None) == 0.0


def test_returns_zero_when_already_cool():
    assert wait_until_cool(80, 68, read=lambda: 70, sleep=lambda s: None) == 0.0


def test_returns_zero_when_initial_read_none():
    assert wait_until_cool(80, 68, read=lambda: None, sleep=lambda s: None) == 0.0


def test_waits_until_resume_temp_and_sums_sleep():
    temps = iter([90, 85, 75, 65])
    slept: list[float] = []
    result = wait_until_cool(80, 68, poll=5.0, read=lambda: next(temps),
                             sleep=lambda s: slept.append(s))
    assert result == 15.0
    assert slept == [5.0, 5.0, 5.0]


def test_stops_when_read_becomes_none_mid_wait():
    temps = iter([90, None])
    result = wait_until_cool(80, 68, poll=2.0, read=lambda: next(temps), sleep=lambda s: None)
    assert result == 2.0


def test_gpu_temperature_returns_none_when_binary_missing(monkeypatch):
    def raise_missing(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr(thermal.subprocess, "run", raise_missing)
    assert thermal.gpu_temperature() is None


def test_raises_at_max_wait_timeout_when_still_hot():
    slept: list[float] = []
    with pytest.raises(RuntimeError, match="GPU still at/above max temp after 20 s"):
        wait_until_cool(78, 68, poll=5.0, read=lambda: 80,
                        sleep=lambda s: slept.append(s), max_wait=20.0)
    assert slept == [5.0, 5.0, 5.0, 5.0]
