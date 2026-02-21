import tempfile
import pytest
import yaml
from pathlib import Path
from journalcheck.journalcheck import load_config
from journalcheck.config import Config, ConfigKeys, IdentifierConfig, IdentifierConfigKeys


def test_load_config_default():
    config = load_config()
    assert config.priority == 6
    assert config.format == "short"
    assert config.identifiers == {}


def test_load_config_from_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({ConfigKeys.PRIORITY: 3, ConfigKeys.FORMAT: "json"}, f)
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


def test_load_config_with_empty_identifiers():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({ConfigKeys.IDENTIFIERS: None}, f)
        config_file = f.name

    try:
        config = load_config(config_file)
        assert config
    finally:
        Path(config_file).unlink()


def test_load_config_with_identifiers_having_empty_ignore_and_violations():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(
            {
                ConfigKeys.IDENTIFIERS: {
                    "kernel": {
                        IdentifierConfigKeys.PRIORITY: 4,
                        IdentifierConfigKeys.IGNORE: None,
                        IdentifierConfigKeys.VIOLATIONS: None,
                    }
                }
            },
            f,
        )
        config_file = f.name

    try:
        config = load_config(config_file)
        assert config.identifiers["kernel"].priority == 4
    finally:
        Path(config_file).unlink()


def test_load_config_priority_names():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({ConfigKeys.PRIORITY: "warning"}, f)
        config_file = f.name

    try:
        config = load_config(config_file)
        assert config.priority == 4
    finally:
        Path(config_file).unlink()


def test_load_config_identifier_int_normalization():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(
            {
                ConfigKeys.IDENTIFIERS: {
                    "kernel": {IdentifierConfigKeys.PRIORITY: "warning"}
                }
            },
            f,
        )
        config_file = f.name

    try:
        config = load_config(config_file)
        assert config.identifiers["kernel"].priority == 4
    finally:
        Path(config_file).unlink()


def test_load_config_raises_yaml_parse_error():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            """
                  priority:6
                  nokey
                  format: short
                """
        )
        config_file = f.name

    try:
        with pytest.raises(yaml.YAMLError):
            load_config(config_file)
    finally:
        Path(config_file).unlink()


def test_load_config_validates_priority():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({ConfigKeys.PRIORITY: 10}, f)
        config_file = f.name

    try:
        with pytest.raises(ValueError, match="Priority must be 0-7"):
            load_config(config_file)
    finally:
        Path(config_file).unlink()


def test_load_config_validates_format():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({ConfigKeys.FORMAT: "invalid"}, f)
        config_file = f.name

    try:
        with pytest.raises(ValueError, match="Format must be"):
            load_config(config_file)
    finally:
        Path(config_file).unlink()


def test_load_config_custom_file_no_default_cursor():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({ConfigKeys.PRIORITY: 6}, f)
        config_file = f.name

    try:
        config = load_config(config_file)
        assert config.cursor_file is None
    finally:
        Path(config_file).unlink()


def test_load_config_custom_file_with_cursor():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({ConfigKeys.CURSOR_FILE: "/tmp/custom_cursor"}, f)
        config_file = f.name

    try:
        config = load_config(config_file)
        assert config.cursor_file == "/tmp/custom_cursor"
    finally:
        Path(config_file).unlink()


def test_load_config_unknown_key():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({ConfigKeys.PRIORITY: 6, "unknown_key": "value"}, f)
        config_file = f.name

    try:
        with pytest.raises(ValueError, match="Unknown keys in config: unknown_key"):
            load_config(config_file)
    finally:
        Path(config_file).unlink()


def test_load_config_invalid_identifiers():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({ConfigKeys.IDENTIFIERS: ["foo"]}, f)
        config_file = f.name

    try:
        with pytest.raises(ValueError, match="must be a dict, got list"):
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
                    ConfigKeys.IDENTIFIERS: {
                        "ssh": {
                            IdentifierConfigKeys.PRIORITY: 6,
                            IdentifierConfigKeys.IGNORE: ["pattern1"],
                            IdentifierConfigKeys.VIOLATIONS: ["violation1"],
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
                    ConfigKeys.IDENTIFIERS: {
                        "ssh": {
                            IdentifierConfigKeys.IGNORE: ["pattern2"],
                            IdentifierConfigKeys.VIOLATIONS: ["violation2"],
                        }
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
            yaml.dump({ConfigKeys.PRIORITY: 6}, f)

        config_dir = Path(tmpdir) / "config.d"
        config_dir.mkdir()

        additional_config = config_dir / "01-additional.yaml"
        with open(additional_config, "w") as f:
            yaml.dump(
                {
                    ConfigKeys.IDENTIFIERS: {
                        "ssh": {IdentifierConfigKeys.PRIORITY: 4}
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
            assert config.identifiers["ssh"].priority == 4
        finally:
            journalcheck.DEFAULT_CONFIG_FILE = original_default_file
            journalcheck.DEFAULT_CONFIG_DIR = original_default_dir


def test_load_config_merge_overrides():
    with tempfile.TemporaryDirectory() as tmpdir:
        main_config = Path(tmpdir) / "main.yaml"
        with open(main_config, "w") as f:
            yaml.dump(
                {
                    ConfigKeys.PRIORITY: 6,
                    ConfigKeys.FORMAT: "short",
                    ConfigKeys.CURSOR_FILE: "/tmp/cursor1",
                },
                f,
            )

        config_dir = Path(tmpdir) / "config.d"
        config_dir.mkdir()

        additional_config = config_dir / "01-additional.yaml"
        with open(additional_config, "w") as f:
            yaml.dump(
                {
                    ConfigKeys.PRIORITY: 4,
                    ConfigKeys.FORMAT: "json",
                    ConfigKeys.CURSOR_FILE: "/tmp/cursor2",
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
            yaml.dump({ConfigKeys.PRIORITY: 6}, f)

        config_dir = Path(tmpdir) / "config.d"
        config_dir.mkdir()

        additional_config = config_dir / "01-additional.yaml"
        with open(additional_config, "w") as f:
            yaml.dump(
                {
                    ConfigKeys.PRIORITY: 4,
                    ConfigKeys.FORMAT: "json",
                    ConfigKeys.CURSOR_FILE: "/tmp/test",
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
            yaml.dump({ConfigKeys.IDENTIFIERS: {"ssh": 4}}, f)

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
            yaml.dump(
                {ConfigKeys.IDENTIFIERS: {"ssh": {IdentifierConfigKeys.PRIORITY: 4}}}, f
            )

        config_dir = Path(tmpdir) / "config.d"
        config_dir.mkdir()

        additional_config = config_dir / "01-additional.yaml"
        with open(additional_config, "w") as f:
            yaml.dump({ConfigKeys.IDENTIFIERS: {"ssh": 6}}, f)

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
            yaml.dump({ConfigKeys.PRIORITY: 6}, f)

        config_dir = Path(tmpdir) / "config.d"
        config_dir.mkdir()

        additional_config = config_dir / "01-additional.yaml"
        with open(additional_config, "w") as f:
            yaml.dump({ConfigKeys.PRIORITY: 4, "unknown_key": "value"}, f)

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
            yaml.dump(
                {
                    ConfigKeys.IDENTIFIERS: {
                        "ssh": {IdentifierConfigKeys.PRIORITY: 4}
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
                    ConfigKeys.IDENTIFIERS: {
                        "ssh": {IdentifierConfigKeys.PRIORITY: 6}
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
            assert config.identifiers["ssh"].priority == 6
        finally:
            journalcheck.DEFAULT_CONFIG_FILE = original_default_file
            journalcheck.DEFAULT_CONFIG_DIR = original_default_dir


def test_load_config_supports_yml_extension():
    with tempfile.TemporaryDirectory() as tmpdir:
        main_config = Path(tmpdir) / "main.yaml"
        with open(main_config, "w") as f:
            yaml.dump({ConfigKeys.PRIORITY: 6}, f)

        config_dir = Path(tmpdir) / "config.d"
        config_dir.mkdir()

        # Create .yml file
        yml_config = config_dir / "01-test.yml"
        with open(yml_config, "w") as f:
            yaml.dump(
                {
                    ConfigKeys.IDENTIFIERS: {
                        "kernel": {IdentifierConfigKeys.PRIORITY: 3}
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
            assert config.identifiers["kernel"].priority == 3
        finally:
            journalcheck.DEFAULT_CONFIG_FILE = original_default_file
            journalcheck.DEFAULT_CONFIG_DIR = original_default_dir


def test_load_config_yml_yaml_sorted_together():
    """Test that .yml and .yaml files are sorted together alphabetically."""
    with tempfile.TemporaryDirectory() as tmpdir:
        main_config = Path(tmpdir) / "main.yaml"
        with open(main_config, "w") as f:
            yaml.dump({ConfigKeys.PRIORITY: 6}, f)

        config_dir = Path(tmpdir) / "config.d"
        config_dir.mkdir()

        # Create files that should be loaded in this order: 01.yaml, 02.yml, 03.yaml
        config_01 = config_dir / "01-first.yaml"
        with open(config_01, "w") as f:
            yaml.dump(
                {
                    ConfigKeys.IDENTIFIERS: {
                        "ssh": {IdentifierConfigKeys.IGNORE: ["pattern1"]}
                    }
                },
                f,
            )

        config_02 = config_dir / "02-second.yml"
        with open(config_02, "w") as f:
            yaml.dump(
                {
                    ConfigKeys.IDENTIFIERS: {
                        "ssh": {IdentifierConfigKeys.IGNORE: ["pattern2"]}
                    }
                },
                f,
            )

        config_03 = config_dir / "03-third.yaml"
        with open(config_03, "w") as f:
            yaml.dump(
                {
                    ConfigKeys.IDENTIFIERS: {
                        "ssh": {IdentifierConfigKeys.IGNORE: ["pattern3"]}
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
            # All three patterns should be present in order
            assert config.identifiers["ssh"].ignore == [
                "pattern1",
                "pattern2",
                "pattern3",
            ]
        finally:
            journalcheck.DEFAULT_CONFIG_FILE = original_default_file
            journalcheck.DEFAULT_CONFIG_DIR = original_default_dir


def test_load_config_default_yml_fallback():
    """Test that .yml is used as fallback if .yaml doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        # Create only .yml file (no .yaml)
        main_config = tmpdir_path / "journalcheck.yml"
        with open(main_config, "w") as f:
            yaml.dump({ConfigKeys.PRIORITY: 3, ConfigKeys.FORMAT: "json"}, f)

        from journalcheck import journalcheck

        original_default_file = journalcheck.DEFAULT_CONFIG_FILE
        original_default_dir = journalcheck.DEFAULT_CONFIG_DIR

        try:
            # Point to .yaml file that doesn't exist
            journalcheck.DEFAULT_CONFIG_FILE = str(tmpdir_path / "journalcheck.yaml")
            journalcheck.DEFAULT_CONFIG_DIR = str(tmpdir_path / "config.d")

            config = load_config()
            # Should load from .yml fallback
            assert config.priority == 3
            assert config.format == "json"
        finally:
            journalcheck.DEFAULT_CONFIG_FILE = original_default_file
            journalcheck.DEFAULT_CONFIG_DIR = original_default_dir
