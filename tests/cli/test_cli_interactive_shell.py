import os
import pytest

import registers.cli as cli


@pytest.fixture(autouse=True)
def _reset_registry():
    cli.reset_registry()
    yield
    cli.reset_registry()


class _TTYStdin:
    def isatty(self) -> bool:
        return True


def _input_from_lines(lines: list[str]):
    iterator = iter(lines)
    def _read(_prompt: str) -> str:
        return next(iterator)
    return _read


def _register_interactive_commands() -> None:
    @cli.register(description="Add item")
    @cli.option("--add")
    @cli.argument("title", type=str)
    def add(title: str) -> str:
        return f"added:{title}"

    @cli.register(description="Run")
    @cli.option("--run")
    @cli.argument("verbose", type=bool)
    def run_cmd(verbose: bool = False) -> str:
        return f"verbose={verbose}"


def test_empty_argv_enters_shell_when_tty(monkeypatch):
    monkeypatch.setattr("registers.cli.registry.sys.stdin", _TTYStdin())

    called: dict[str, object] = {}

    def _fake_run_shell(**kwargs):
        called.update(kwargs)
        return "shell-entered"

    monkeypatch.setattr(cli.get_registry(), "run_shell", _fake_run_shell)

    result = cli.run([], print_result=False)

    assert result == "shell-entered"
    assert called["print_result"] is False


def test_interactive_flag_enters_shell(monkeypatch):
    called = {"count": 0}

    def _fake_run_shell(**_kwargs):
        called["count"] += 1
        return None

    monkeypatch.setattr(cli.get_registry(), "run_shell", _fake_run_shell)

    assert cli.run(["--interactive"], print_result=False) is None
    assert cli.run(["-i"], print_result=False) is None
    assert called["count"] == 2


def test_interactive_mode_dispatches_registered_commands(capsys):
    _register_interactive_commands()

    cli.run_shell(
        input_fn=_input_from_lines(
            [
                "add Alpha",
                "--add Beta",
                "add --title Gamma",
                "run",
                "run --verbose",
                "exit",
            ]
        )
    )

    out = capsys.readouterr().out
    assert "added:Alpha" in out
    assert "added:Beta" in out
    assert "added:Gamma" in out
    assert "verbose=False" in out
    assert "verbose=True" in out


def test_interactive_mode_keeps_running_after_parse_and_unknown_errors(capsys):
    _register_interactive_commands()

    cli.run_shell(
        input_fn=_input_from_lines(
            [
                "add",
                "ad",
                "add Working",
                "exit",
            ]
        )
    )

    out = capsys.readouterr().out
    assert "Missing required argument 'title'" in out
    assert "Did you mean 'add'" in out
    assert "added:Working" in out


def test_run_supports_cli_args_even_when_shell_options_are_provided():
    _register_interactive_commands()

    def _should_not_be_called(_prompt: str) -> str:
        raise AssertionError("shell_input_fn should not be used when argv has a command")

    result = cli.run(
        ["add", "ViaArgs"],
        print_result=False,
        shell_input_fn=_should_not_be_called,
        shell_title="Custom Shell Title",
        shell_description="Custom description",
    )

    assert result == "added:ViaArgs"


def test_interactive_mode_supports_exec_builtin(capsys, monkeypatch):
    _register_interactive_commands()

    calls: list[list[str]] = []

    class _Result:
        returncode = 0
        stdout = "exec-ok\n"
        stderr = ""

    def _fake_run(argv, capture_output, text):
        assert capture_output is True
        assert text is True
        calls.append(argv)
        return _Result()

    monkeypatch.setattr("registers.cli.shell.subprocess.run", _fake_run)

    cli.run_shell(
        input_fn=_input_from_lines(["exec echo hello world", "quit"]),
        print_result=False,
        banner=False,
        colors=False,
    )

    out = capsys.readouterr().out
    assert "exec-ok" in out
    assert calls
    if os.name == "nt":
        assert calls[0][:4] == ["powershell", "-NoLogo", "-NoProfile", "-Command"]
        assert calls[0][4] == "echo hello world"
    else:
        assert calls[0][:2] == ["bash", "-lc"]
        assert calls[0][2] == "echo hello world"


def test_exec_falls_back_to_cmd_when_powershell_missing(capsys, monkeypatch):
    _register_interactive_commands()

    calls: list[str] = []

    class _Result:
        returncode = 0
        stdout = "fallback-ok\n"
        stderr = ""

    def _fake_run(argv, capture_output, text):
        calls.append(argv[0])
        if argv[0] == "powershell":
            raise FileNotFoundError("powershell missing")
        return _Result()

    monkeypatch.setattr("registers.cli.shell._is_windows", lambda: True)
    monkeypatch.setattr("registers.cli.shell.subprocess.run", _fake_run)

    cli.run_shell(
        input_fn=_input_from_lines(["exec echo from-cmd", "quit"]),
        print_result=False,
        banner=False,
        colors=False,
    )

    out = capsys.readouterr().out
    assert "fallback-ok" in out
    assert calls == ["powershell", "cmd"]


def test_exec_requires_command_text(capsys):
    _register_interactive_commands()

    cli.run_shell(
        input_fn=_input_from_lines(["exec", "quit"]),
        print_result=False,
        banner=False,
        colors=False,
    )

    out = capsys.readouterr().out
    assert "'exec' requires a command to run." in out
