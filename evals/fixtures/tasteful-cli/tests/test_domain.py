from tasteful_cli.domain import Event, parse_event, summarize


def test_parse_event() -> None:
    assert parse_event("signup,3") == Event(kind="signup", value=3)


def test_summarize() -> None:
    assert summarize([Event("signup", 3), Event("signup", 2), Event("login", 5)]) == {
        "login": 5,
        "signup": 5,
    }
