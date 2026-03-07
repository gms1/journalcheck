from datetime import datetime
from journalcheck.config import OutputFormat
from journalcheck.journalcheck import (
    Severity,
    format_entry,
    get_identifier,
    format_identifier_with_pid,
    JournalFields,
)


def test_get_identifier_syslog():
    entry = {JournalFields.SYSLOG_IDENTIFIER: "test"}
    assert get_identifier(entry) == "test"


def test_get_identifier_comm():
    entry = {JournalFields.COMM: "testcomm"}
    assert get_identifier(entry) == "testcomm"


def test_get_identifier_empty():
    entry = {}
    assert get_identifier(entry) == ""


def test_format_identifier_with_pid_syslog():
    entry = {JournalFields.SYSLOG_IDENTIFIER: "test", JournalFields.PID: 1234}
    assert format_identifier_with_pid(entry) == "test[1234]"


def test_format_identifier_with_pid_comm():
    entry = {JournalFields.COMM: "test", JournalFields.PID: 1234}
    assert format_identifier_with_pid(entry) == "(test)[1234]"


def test_format_identifier_with_pid_no_pid():
    entry = {JournalFields.SYSLOG_IDENTIFIER: "test"}
    assert format_identifier_with_pid(entry) == "test"


def test_format_identifier_with_pid_no_syslog_no_comm():
    entry = {JournalFields.PID: 1234}
    assert format_identifier_with_pid(entry) == "[1234]"


def test_format_entry_json():
    entry = {JournalFields.MESSAGE: "test", JournalFields.HOSTNAME: "host"}
    result = format_entry(entry, OutputFormat.JSON, Severity.VIOLATION)
    assert "test" in result
    assert "host" in result
    assert Severity.VIOLATION in result


def test_format_entry_short():
    entry = {
        JournalFields.REALTIME_TIMESTAMP: datetime(2024, 1, 1, 12, 0, 0),
        JournalFields.HOSTNAME: "testhost",
        JournalFields.SYSLOG_IDENTIFIER: "testapp",
        JournalFields.MESSAGE: "test message",
    }
    result = format_entry(entry, OutputFormat.SHORT)
    assert "testhost" in result
    assert "testapp" in result
    assert "test message" in result


def test_format_entry_with_pid():
    entry = {
        JournalFields.REALTIME_TIMESTAMP: 4321,
        JournalFields.HOSTNAME: "testhost",
        JournalFields.SYSLOG_IDENTIFIER: "testapp",
        JournalFields.PID: 1234,
        JournalFields.MESSAGE: "test message",
    }
    result = format_entry(entry, OutputFormat.SHORT)
    assert "4321" in result
    assert "testapp[1234]" in result


def test_format_entry_without_timestamp():
    entry = {
        JournalFields.HOSTNAME: "testhost",
        JournalFields.SYSLOG_IDENTIFIER: "testapp",
        JournalFields.MESSAGE: "test message",
    }
    result = format_entry(entry, OutputFormat.SHORT)
    assert datetime.now().strftime("%b %d") in result
