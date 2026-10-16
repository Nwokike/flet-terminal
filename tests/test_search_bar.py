"""TerminalSearchBar: stepping math, match counter, and close behavior."""

from flet_terminal import TerminalSearchBar


def _bar():
    calls: list[tuple[str, int, str]] = []
    closed: list[int] = []
    bar = TerminalSearchBar(
        on_search=lambda q, s, d: calls.append((q, s, d)),
        on_close=lambda: closed.append(1),
    )
    return bar, calls, closed


def test_empty_query_is_a_noop():
    bar, calls, _ = _bar()
    bar.do_search(direction="next")
    assert calls == []


def test_fresh_query_starts_at_zero():
    bar, calls, _ = _bar()
    bar._search_field.value = "needle"
    bar.do_search(direction="next", reset=True)
    assert calls == [("needle", 0, "next")]
    assert bar._last_query == "needle"


def test_stepping_uses_reported_index():
    bar, calls, _ = _bar()
    bar._search_field.value = "needle"
    bar.do_search(direction="next", reset=True)
    bar.report_result(found=True, count=5, index=2)

    bar.do_search(direction="next")
    assert calls[-1] == ("needle", 3, "next")

    bar.do_search(direction="prev")
    assert calls[-1] == ("needle", 2, "prev")


def test_new_query_resets_position():
    bar, calls, _ = _bar()
    bar._search_field.value = "needle"
    bar.do_search(direction="next", reset=True)
    bar.report_result(found=True, count=5, index=4)

    bar._search_field.value = "other"
    bar.do_search(direction="next")
    assert calls[-1] == ("other", 0, "next")


def test_not_found_resets_last_index():
    bar, calls, _ = _bar()
    bar._search_field.value = "needle"
    bar.do_search(direction="next", reset=True)
    bar.report_result(found=False, count=0, index=-1)
    bar.do_search(direction="next")
    assert calls[-1] == ("needle", 0, "next")


def test_report_result_counter_text():
    bar, _, _ = _bar()
    bar.report_result(found=True, count=3, index=0)
    assert bar._counter.value == "3 found"
    assert bar._counter.visible is True

    bar.report_result(found=False, count=0, index=-1)
    assert bar._counter.value == "No matches"


def test_close_resets_state_and_fires_callback():
    bar, _, closed = _bar()
    bar._search_field.value = "needle"
    bar.report_result(found=True, count=3, index=1)

    bar._handle_close()
    assert closed == [1]
    assert bar._search_field.value == ""
    assert bar._counter.visible is False
    assert bar._last_index == -1
    assert bar._last_query is None
    assert bar._count == 0
