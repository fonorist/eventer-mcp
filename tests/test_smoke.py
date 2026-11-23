"""Fast checks for the package and the command line (no server is actually started)."""

import pytest

import eventer_mcp
from eventer_mcp import cli


def test_package_has_version() -> None:
    assert eventer_mcp.__version__


def test_cli_default_is_stdio() -> None:
    args = cli.build_parser().parse_args(["run"])
    assert args.transport == "stdio"


def test_cli_http_not_ready_yet() -> None:
    # Exit code 2 = "can't do that yet". Replaced by a real test in M6.
    assert cli.main(["run", "--transport", "http"]) == 2


def test_cli_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    # argparse prints the version and exits; capsys captures what was printed.
    with pytest.raises(SystemExit):
        cli.main(["--version"])
    assert "eventer-mcp" in capsys.readouterr().out


# parametrize = run this same test 3 times, once per argv value.
@pytest.mark.parametrize("argv", [[], ["run"], ["run", "--transport", "stdio"]])
def test_cli_runs_stdio_server(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> None:
    from eventer_mcp.app import mcp

    # monkeypatch temporarily swaps mcp.run for a fake that only records its argument,
    # so we can check main() starts stdio without actually blocking on a real server.
    # The original is restored automatically after the test.
    calls: list[str] = []
    monkeypatch.setattr(mcp, "run", lambda transport: calls.append(transport))
    assert cli.main(argv) == 0
    assert calls == ["stdio"]
