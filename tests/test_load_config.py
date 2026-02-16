import tempfile
import yaml
from pathlib import Path
import pytest
from journalcheck.journalcheck import load_config
from journalcheck.config import Config, IdentifierConfig


def test_load_config_default():
    config = load_config()
    assert config.priority == 6
    assert config.format == "short"
    assert config.identifiers == {}


def test_load_config_from_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"priority": 3, "format": "json"}, f)
        config_file = f.name

    try:
        config = load_config(config_file)
        assert config.priority == 3
        assert config.format == "json"
    finally:
        Path(config_file).unlink()


def test_load_config_with_args():
    config = load_config(priority_param=4, output_format_param="json")
    assert config.priority == 4
    assert config.format == "json"


def test_load_config_with_identifiers():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"identifiers": {"kernel": {"priority": 4}}}, f)
        config_file = f.name

    try:
        config = load_config(config_file)
        assert config.identifiers["kernel"].priority == 4
    finally:
        Path(config_file).unlink()


def test_load_config_priority_names():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"priority": "warning"}, f)
        config_file = f.name

    try:
        config = load_config(config_file)
        assert config.priority == 4
    finally:
        Path(config_file).unlink()


def test_load_config_identifier_int_normalization():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"identifiers": {"kernel": {"priority": "warning"}}}, f)
        config_file = f.name

    try:
        config = load_config(config_file)
        assert config.identifiers["kernel"].priority == 4
    finally:
        Path(config_file).unlink()


def test_load_config_validates_priority():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"priority": 10}, f)
        config_file = f.name

    try:
        with pytest.raises(ValueError, match="Priority must be 0-7"):
            load_config(config_file)
    finally:
        Path(config_file).unlink()


def test_load_config_validates_format():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"format": "invalid"}, f)
        config_file = f.name

    try:
        with pytest.raises(ValueError, match="Format must be"):
            load_config(config_file)
    finally:
        Path(config_file).unlink()


def test_load_config_custom_file_no_default_cursor():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"priority": 6}, f)
        config_file = f.name

    try:
        config = load_config(config_file)
        assert config.cursor_file is None
    finally:
        Path(config_file).unlink()


def test_load_config_custom_file_with_cursor():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"cursor_file": "/tmp/custom_cursor"}, f)
        config_file = f.name

    try:
        config = load_config(config_file)
        assert config.cursor_file == "/tmp/custom_cursor"
    finally:
        Path(config_file).unlink()


def test_load_config_unknown_key():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"priority": 6, "unknown_key": "value"}, f)
        config_file = f.name

    try:
        with pytest.raises(ValueError, match="Unknown keys in config: unknown_key"):
            load_config(config_file)
    finally:
        Path(config_file).unlink()


def test_load_config_file_not_found():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        config_file = f.name
    Path(config_file).unlink()
    with pytest.raises(
        FileNotFoundError, match=f"Config file not found: {config_file}"
    ):
        load_config(config_file)


def test_load_config_merge_appends_lists():
    with tempfile.TemporaryDirectory() as tmpdir:
        main_config = Path(tmpdir) / "main.yaml"
        with open(main_config, "w") as f:
            yaml.dump(
                {
                    "identifiers": {
                        "ssh": {
                            "priority": 6,
                            "ignore": ["pattern1"],
                            "violations": ["violation1"],
                        }
                    }
                },
                f,
            )

        config_dir = Path(tmpdir) / "config.d"
        config_dir.mkdir()

        additional_config = config_dir / "01-additional.yaml"
        with open(additional_config, "w") as f:
            yaml.dump(
                {
                    "identifiers": {
                        "ssh": {"ignore": ["pattern2"], "violations": ["violation2"]}
                    }
                },
                f,
            )

        from journalcheck import journalcheck

        original_default_file = journalcheck.DEFAULT_CONFIG_FILE
        original_default_dir = journalcheck.DEFAULT_CONFIG_DIR

        try:
            journalcheck.DEFAULT_CONFIG_FILE = str(main_config)
            journalcheck.DEFAULT_CONFIG_DIR = str(config_dir)

            config = load_config()

            assert isinstance(config.identifiers["ssh"], IdentifierConfig)
            assert config.identifiers["ssh"].ignore == ["pattern1", "pattern2"]
            assert config.identifiers["ssh"].violations == ["violation1", "violation2"]
            assert config.identifiers["ssh"].priority == 6
        finally:
            journalcheck.DEFAULT_CONFIG_FILE = original_default_file
            journalcheck.DEFAULT_CONFIG_DIR = original_default_dir


def test_load_config_merge_no_identifiers_in_main():
    with tempfile.TemporaryDirectory() as tmpdir:
        main_config = Path(tmpdir) / "main.yaml"
        with open(main_config, "w") as f:
            yaml.dump({"priority": 6}, f)

        config_dir = Path(tmpdir) / "config.d"
        config_dir.mkdir()

        additional_config = config_dir / "01-additional.yaml"
        with open(additional_config, "w") as f:
            yaml.dump({"identifiers": {"ssh": {"priority": 4}}}, f)

        from journalcheck import journalcheck

        original_default_file = journalcheck.DEFAULT_CONFIG_FILE
        original_default_dir = journalcheck.DEFAULT_CONFIG_DIR

        try:
            journalcheck.DEFAULT_CONFIG_FILE = str(main_config)
            journalcheck.DEFAULT_CONFIG_DIR = str(config_dir)

            config = load_config()
            assert isinstance(config.identifiers["ssh"], IdentifierConfig)
            assert config.identifiers["ssh"].priority == 4
        finally:
            journalcheck.DEFAULT_CONFIG_FILE = original_default_file
            journalcheck.DEFAULT_CONFIG_DIR = original_default_dir


def test_load_config_merge_overrides():
    with tempfile.TemporaryDirectory() as tmpdir:
        main_config = Path(tmpdir) / "main.yaml"
        with open(main_config, "w") as f:
            yaml.dump(
                {"priority": 6, "format": "short", "cursor_file": "/tmp/cursor1"}, f
            )

        config_dir = Path(tmpdir) / "config.d"
        config_dir.mkdir()

        additional_config = config_dir / "01-additional.yaml"
        with open(additional_config, "w") as f:
            yaml.dump(
                {"priority": 4, "format": "json", "cursor_file": "/tmp/cursor2"}, f
            )

        from journalcheck import journalcheck

        original_default_file = journalcheck.DEFAULT_CONFIG_FILE
        original_default_dir = journalcheck.DEFAULT_CONFIG_DIR

        try:
            journalcheck.DEFAULT_CONFIG_FILE = str(main_config)
            journalcheck.DEFAULT_CONFIG_DIR = str(config_dir)

            config = load_config()
            assert config.priority == 4
            assert config.format == "json"
            assert config.cursor_file == "/tmp/cursor2"
        finally:
            journalcheck.DEFAULT_CONFIG_FILE = original_default_file
            journalcheck.DEFAULT_CONFIG_DIR = original_default_dir


def test_load_config_merge_overrides_no_identifiers():
    with tempfile.TemporaryDirectory() as tmpdir:
        main_config = Path(tmpdir) / "main.yaml"
        with open(main_config, "w") as f:
            yaml.dump({"priority": 6}, f)

        config_dir = Path(tmpdir) / "config.d"
        config_dir.mkdir()

        additional_config = config_dir / "01-additional.yaml"
        with open(additional_config, "w") as f:
            yaml.dump({"priority": 4, "format": "json", "cursor_file": "/tmp/test"}, f)

        from journalcheck import journalcheck

        original_default_file = journalcheck.DEFAULT_CONFIG_FILE
        original_default_dir = journalcheck.DEFAULT_CONFIG_DIR

        try:
            journalcheck.DEFAULT_CONFIG_FILE = str(main_config)
            journalcheck.DEFAULT_CONFIG_DIR = str(config_dir)

            config = load_config()
            assert config.priority == 4
            assert config.format == "json"
            assert config.cursor_file == "/tmp/test"
        finally:
            journalcheck.DEFAULT_CONFIG_FILE = original_default_file
            journalcheck.DEFAULT_CONFIG_DIR = original_default_dir


def test_load_config_merge_non_dict_identifier():
    with tempfile.TemporaryDirectory() as tmpdir:
        main_config = Path(tmpdir) / "main.yaml"
        with open(main_config, "w") as f:
            yaml.dump({"identifiers": {"ssh": 4}}, f)

        from journalcheck import journalcheck

        original_default_file = journalcheck.DEFAULT_CONFIG_FILE

        try:
            journalcheck.DEFAULT_CONFIG_FILE = str(main_config)

            with pytest.raises(ValueError, match="Identifier 'ssh' must be a dict"):
                load_config()
        finally:
            journalcheck.DEFAULT_CONFIG_FILE = original_default_file


def test_load_config_merge_dict_to_int_identifier():
    with tempfile.TemporaryDirectory() as tmpdir:
        main_config = Path(tmpdir) / "main.yaml"
        with open(main_config, "w") as f:
            yaml.dump({"identifiers": {"ssh": {"priority": 4}}}, f)

        config_dir = Path(tmpdir) / "config.d"
        config_dir.mkdir()

        additional_config = config_dir / "01-additional.yaml"
        with open(additional_config, "w") as f:
            yaml.dump({"identifiers": {"ssh": 6}}, f)

        from journalcheck import journalcheck

        original_default_file = journalcheck.DEFAULT_CONFIG_FILE
        original_default_dir = journalcheck.DEFAULT_CONFIG_DIR

        try:
            journalcheck.DEFAULT_CONFIG_FILE = str(main_config)
            journalcheck.DEFAULT_CONFIG_DIR = str(config_dir)

            with pytest.raises(ValueError, match="Identifier 'ssh' must be a dict"):
                load_config()
        finally:
            journalcheck.DEFAULT_CONFIG_FILE = original_default_file
            journalcheck.DEFAULT_CONFIG_DIR = original_default_dir


def test_load_config_unknown_key_in_config_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        main_config = Path(tmpdir) / "main.yaml"
        with open(main_config, "w") as f:
            yaml.dump({"priority": 6}, f)

        config_dir = Path(tmpdir) / "config.d"
        config_dir.mkdir()

        additional_config = config_dir / "01-additional.yaml"
        with open(additional_config, "w") as f:
            yaml.dump({"priority": 4, "unknown_key": "value"}, f)

        from journalcheck import journalcheck

        original_default_file = journalcheck.DEFAULT_CONFIG_FILE
        original_default_dir = journalcheck.DEFAULT_CONFIG_DIR

        try:
            journalcheck.DEFAULT_CONFIG_FILE = str(main_config)
            journalcheck.DEFAULT_CONFIG_DIR = str(config_dir)

            with pytest.raises(ValueError, match="Unknown keys in config: unknown_key"):
                load_config()
        finally:
            journalcheck.DEFAULT_CONFIG_FILE = original_default_file
            journalcheck.DEFAULT_CONFIG_DIR = original_default_dir


def test_load_config_merge_priority_override():
    with tempfile.TemporaryDirectory() as tmpdir:
        main_config = Path(tmpdir) / "main.yaml"
        with open(main_config, "w") as f:
            yaml.dump({"identifiers": {"ssh": {"priority": 4}}}, f)

        config_dir = Path(tmpdir) / "config.d"
        config_dir.mkdir()

        additional_config = config_dir / "01-additional.yaml"
        with open(additional_config, "w") as f:
            yaml.dump({"identifiers": {"ssh": {"priority": 6}}}, f)

        from journalcheck import journalcheck

        original_default_file = journalcheck.DEFAULT_CONFIG_FILE
        original_default_dir = journalcheck.DEFAULT_CONFIG_DIR

        try:
            journalcheck.DEFAULT_CONFIG_FILE = str(main_config)
            journalcheck.DEFAULT_CONFIG_DIR = str(config_dir)

            config = load_config()
            assert config.identifiers["ssh"].priority == 6
        finally:
            journalcheck.DEFAULT_CONFIG_FILE = original_default_file
            journalcheck.DEFAULT_CONFIG_DIR = original_default_dir
