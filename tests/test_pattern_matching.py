from journalcheck.journalcheck import should_show_entry, JournalFields
from journalcheck.config import Config, IdentifierConfig


def test_should_show_entry_default():
    config = Config(priority=6)
    entry = {"PRIORITY": 5}
    show, severity = should_show_entry(entry, config)
    assert show is True
    assert severity == ""


def test_should_show_entry_filtered():
    config = Config(priority=4)
    entry = {"PRIORITY": 5}
    show, severity = should_show_entry(entry, config)
    assert show is False


def test_should_show_entry_identifier_dict():
    config = Config(priority=6, identifiers={"kernel": IdentifierConfig(priority=4)})
    entry = {"SYSLOG_IDENTIFIER": "kernel", "PRIORITY": 5}
    show, severity = should_show_entry(entry, config)
    assert show is False


def test_should_show_entry_identifier_int():
    config = Config(priority=6, identifiers={"kernel": IdentifierConfig(priority=4)})
    entry = {"SYSLOG_IDENTIFIER": "kernel", "PRIORITY": 3}
    show, severity = should_show_entry(entry, config)
    assert show is True


def test_should_show_entry_regex_match():
    config = Config(
        priority=6, identifiers={"/^systemd.*/": IdentifierConfig(priority=4)}
    )
    entry = {"SYSLOG_IDENTIFIER": "systemd-logind", "PRIORITY": 5}
    show, severity = should_show_entry(entry, config)
    assert show is False


def test_should_show_entry_regex_no_match():
    config = Config(
        priority=6, identifiers={"/^systemd.*/": IdentifierConfig(priority=4)}
    )
    entry = {"SYSLOG_IDENTIFIER": "kernel", "PRIORITY": 5}
    show, severity = should_show_entry(entry, config)
    assert show is True


def test_should_show_entry_regex_int():
    config = Config(priority=6, identifiers={"/^systemd.*/": IdentifierConfig(priority=3)})
    entry = {"SYSLOG_IDENTIFIER": "systemd-udevd", "PRIORITY": 3}
    show, severity = should_show_entry(entry, config)
    assert show is True


def test_should_show_entry_violation():
    config = Config(
        priority=6, identifiers={"ssh": IdentifierConfig(violations=["Failed"])}
    )
    entry = {"SYSLOG_IDENTIFIER": "ssh", "PRIORITY": 6, "MESSAGE": "Failed password"}
    show, severity = should_show_entry(entry, config)
    assert show is True
    assert severity == "VIOLATION"


def test_should_show_entry_ignore():
    config = Config(
        priority=6, identifiers={"ssh": IdentifierConfig(ignore=[".*Accepted.*"])}
    )
    entry = {"SYSLOG_IDENTIFIER": "ssh", "PRIORITY": 6, "MESSAGE": "Accepted publickey"}
    show, severity = should_show_entry(entry, config)
    assert show is False


def test_should_show_entry_regex_violation():
    config = Config(
        priority=6, identifiers={"/^ssh.*/": IdentifierConfig(violations=["Failed"])}
    )
    entry = {"SYSLOG_IDENTIFIER": "sshd", "PRIORITY": 6, "MESSAGE": "Failed password"}
    show, severity = should_show_entry(entry, config)
    assert show is True
    assert severity == "VIOLATION"


def test_should_show_entry_regex_ignore():
    config = Config(
        priority=6, identifiers={"/^ssh.*/": IdentifierConfig(ignore=[".*Accepted.*"])}
    )
    entry = {
        "SYSLOG_IDENTIFIER": "sshd",
        "PRIORITY": 6,
        "MESSAGE": "Accepted publickey",
    }
    show, severity = should_show_entry(entry, config)
    assert show is False


def test_ignore_pattern_fullmatch():
    config = Config(
        priority=6,
        identifiers={"test": IdentifierConfig(ignore=["connection accepted"])},
    )
    entry = {
        "SYSLOG_IDENTIFIER": "test",
        "PRIORITY": 6,
        "MESSAGE": "connection accepted",
    }
    show, severity = should_show_entry(entry, config)
    assert show is False

    entry2 = {
        "SYSLOG_IDENTIFIER": "test",
        "PRIORITY": 6,
        "MESSAGE": "prefix connection accepted suffix",
    }
    show2, severity2 = should_show_entry(entry2, config)
    assert show2 is True


def test_violation_pattern_search():
    config = Config(
        priority=6, identifiers={"test": IdentifierConfig(violations=["failed"])}
    )
    entry = {
        "SYSLOG_IDENTIFIER": "test",
        "PRIORITY": 6,
        "MESSAGE": "authentication failed for user",
    }
    show, severity = should_show_entry(entry, config)
    assert show is True
    assert severity == "VIOLATION"

    entry2 = {
        "SYSLOG_IDENTIFIER": "test",
        "PRIORITY": 6,
        "MESSAGE": "prefix failed suffix",
    }
    show2, severity2 = should_show_entry(entry2, config)
    assert show2 is True
    assert severity2 == "VIOLATION"


def test_violation_pattern_case_insensitive():
    config = Config(
        priority=6, identifiers={"test": IdentifierConfig(violations=["Failed"])}
    )
    entry = {
        JournalFields.SYSLOG_IDENTIFIER: "test",
        JournalFields.PRIORITY: 6,
        JournalFields.MESSAGE: "FAILED password",
    }
    show, severity = should_show_entry(entry, config)
    assert show is True
    assert severity == "VIOLATION"


def test_ignore_pattern_case_insensitive():
    config = Config(
        priority=6,
        identifiers={"test": IdentifierConfig(ignore=["accepted publickey"])},
    )
    entry = {
        JournalFields.SYSLOG_IDENTIFIER: "test",
        JournalFields.PRIORITY: 6,
        JournalFields.MESSAGE: "Accepted Publickey",
    }
    show, severity = should_show_entry(entry, config)
    assert show is False
