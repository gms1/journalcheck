from datetime import datetime
from journalcheck.journalcheck import (
    format_entry,
    get_identifier,
    format_identifier_with_pid,
)


def test_get_identifier_syslog():
    entry = {"SYSLOG_IDENTIFIER": "test"}
    assert get_identifier(entry) == "test"


def test_get_identifier_comm():
    entry = {"_COMM": "testcomm"}
    assert get_identifier(entry) == "testcomm"


def test_get_identifier_empty():
    entry = {}
    assert get_identifier(entry) == ""


def test_format_identifier_with_pid_syslog():
    entry = {"SYSLOG_IDENTIFIER": "test", "_PID": 1234}
    assert format_identifier_with_pid(entry) == "test[1234]"


def test_format_identifier_with_pid_comm():
    entry = {"_COMM": "test", "_PID": 1234}
    assert format_identifier_with_pid(entry) == "(test)[1234]"


def test_format_identifier_with_pid_no_pid():
    entry = {"SYSLOG_IDENTIFIER": "test"}
    assert format_identifier_with_pid(entry) == "test"


def test_format_entry_json():
    entry = {"MESSAGE": "test", "_HOSTNAME": "host"}
    result = format_entry(entry, "json")
    assert "test" in result
    assert "host" in result


def test_format_entry_short():
    entry = {
        "__REALTIME_TIMESTAMP": datetime(2024, 1, 1, 12, 0, 0),
        "_HOSTNAME": "testhost",
        "SYSLOG_IDENTIFIER": "testapp",
        "MESSAGE": "test message",
    }
    result = format_entry(entry, "short")
    assert "testhost" in result
    assert "testapp" in result
    assert "test message" in result


def test_format_entry_with_pid():
    entry = {
        "__REALTIME_TIMESTAMP": datetime(2024, 1, 1, 12, 0, 0),
        "_HOSTNAME": "testhost",
        "SYSLOG_IDENTIFIER": "testapp",
        "_PID": 1234,
        "MESSAGE": "test message",
    }
    result = format_entry(entry, "short")
    assert "testapp[1234]" in result
