from journalcheck.config import OutputFormat
from journalcheck.journalcheck import _parse_args


def test_parse_args_defaults():
    args = _parse_args([])
    assert args.config is None
    assert args.priority is None
    assert args.output is None


def test_parse_args_with_options():
    args = _parse_args(["-c", "test.yaml", "-p", "3", "-o", OutputFormat.JSON])
    assert args.config == "test.yaml"
    assert args.priority == 3
    assert args.output == OutputFormat.JSON


def test_parse_args_with_test_option():
    args = _parse_args(["-t"])
    assert args.test is True


def test_parse_args_without_test_option():
    args = _parse_args([])
    assert args.test is False


def test_parse_args_with_show_config():
    args = _parse_args(["--show-config"])
    assert args.show_config is True
