from mock_virtuoso.cli import main


def test_eval_prints_result(capsys):
    assert main(["eval", "1+2"]) == 0
    assert capsys.readouterr().out.strip() == "3"


def test_eval_reports_unknown_function(capsys):
    assert main(["eval", "noSuchFn()"]) == 1
    assert "unknown function: noSuchFn" in capsys.readouterr().err


def test_no_command_returns_error():
    assert main([]) == 2
