from cleanup_export import render_handoff


def test_render_handoff_normalizes_export_lines() -> None:
    raw_export = """
    database failover   completed

    alerts acknowledged
    """

    assert (
        render_handoff(raw_export)
        == "- database failover completed\n- alerts acknowledged\n"
    )
