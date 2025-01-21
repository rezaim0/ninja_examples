# test_config.py

import os
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch
from typing import Dict, Any, Generator, List

# Pytest fixtures for capturing logs and patching environment
from _pytest.logging import LogCaptureFixture
from _pytest.monkeypatch import MonkeyPatch

# Import from your code under test
from config_code import (
    load_config,
    get_user_id,
    get_db_config,
    DBConfig,
    Environment
)


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_config() -> Dict[str, Dict[str, Any]]:
    """
    Returns a dictionary that mimics a typical YAML config structure 
    for multiple environments.

    Returns:
        Dict[str, Dict[str, Any]]: A nested dictionary mapping environment
        names to their respective database configs.
    """
    return {
        "local": {
            "database": "local_db",
            "schema": "public",
            "table_names": [
                "fields_table",
                "version_table",
                "output_table"
            ]
        },
        "dev": {
            "database": "dev_db",
            "schema": "dev_schema",
            "table_names": [
                "fields_dev_table",
                "version_dev_table",
                "output_dev_table"
            ]
        },
        "staging": {
            "database": "stage_db",
            "schema": "stage_schema",
            "table_names": [
                "fields_staging_table",
                "version_staging_table",
                "output_staging_table"
            ]
        },
        "prod": {
            "database": "prod_db",
            "schema": "prod_schema",
            "table_names": [
                "fields_prod_table",
                "version_prod_table",
                "output_prod_table"
            ]
        }
    }


@pytest.fixture
def config_file(
    tmp_path: Path, 
    sample_config: Dict[str, Dict[str, Any]]
) -> Generator[Path, None, None]:
    """
    Creates a temporary config file from the sample_config fixture,
    then yields the path to that file.

    Args:
        tmp_path (Path): A pytest fixture providing a temporary directory unique to each test.
        sample_config (Dict[str, Dict[str, Any]]): The in-memory configuration data to write to YAML.

    Yields:
        Path: The path to the temporary YAML file containing the sample configuration.
    """
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(sample_config, f)
    yield config_path


# ---------------------------------------------------------------------------
# TESTS for load_config
# ---------------------------------------------------------------------------

def test_load_config_success(config_file: Path) -> None:
    """
    Test that load_config properly loads valid YAML from a given path.

    Args:
        config_file (Path): Path to a temporary YAML file containing valid config data.
    """
    config = load_config(config_path=str(config_file))
    assert isinstance(config, dict)
    # We expect 'local', 'dev', 'staging', 'prod' sections
    for env in ["local", "dev", "staging", "prod"]:
        assert env in config


def test_load_config_missing_file(tmp_path: Path) -> None:
    """
    Test that load_config raises an error if the file does not exist.

    Args:
        tmp_path (Path): A pytest fixture for a unique temporary directory.
    """
    fake_path = tmp_path / "non_existent.yaml"
    with pytest.raises(FileNotFoundError):
        load_config(config_path=str(fake_path))


def test_load_config_invalid_yaml(tmp_path: Path) -> None:
    """
    Test that load_config raises an exception if the file is not valid YAML.

    Args:
        tmp_path (Path): A pytest fixture for a unique temporary directory.
    """
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("::: not valid yaml :::", encoding="utf-8")
    with pytest.raises(Exception) as excinfo:
        load_config(config_path=str(bad_file))
    # Depending on PyYAML version, it could raise YAMLError or other exceptions.
    # Just ensure it fails with some YAML-related error.
    assert "could not" in str(excinfo.value).lower() or "yaml" in str(excinfo.value).lower()


# ---------------------------------------------------------------------------
# TESTS for get_user_id
# ---------------------------------------------------------------------------

def test_get_user_id_valid(
    monkeypatch: MonkeyPatch
) -> None:
    """
    Test get_user_id when NB_PREFIX has a valid format, e.g. /user/foo/u1234/edit.

    Args:
        monkeypatch (MonkeyPatch): Fixture for modifying environment variables safely.
    """
    mock_prefix = "/notebooks/namespace/u1234-abc/edit"
    monkeypatch.setenv("NB_PREFIX", mock_prefix)
    user_id = get_user_id()
    assert user_id == "u1234"


def test_get_user_id_no_env(
    monkeypatch: MonkeyPatch, 
    caplog: LogCaptureFixture
) -> None:
    """
    Test get_user_id when NB_PREFIX is not set at all.
    Also check the log message.

    Args:
        monkeypatch (MonkeyPatch): Fixture for modifying environment variables safely.
        caplog (LogCaptureFixture): Fixture to capture log outputs.
    """
    monkeypatch.delenv("NB_PREFIX", raising=False)
    user_id = get_user_id()
    assert user_id is None
    assert any("NB_PREFIX environment variable is not set" in rec.message for rec in caplog.records)


def test_get_user_id_wrong_length(
    monkeypatch: MonkeyPatch, 
    caplog: LogCaptureFixture
) -> None:
    """
    Test get_user_id when the extracted user ID is not 5 chars long.

    Args:
        monkeypatch (MonkeyPatch): Fixture for modifying environment variables safely.
        caplog (LogCaptureFixture): Fixture to capture log outputs.
    """
    mock_prefix = "/path/u123456-other"
    monkeypatch.setenv("NB_PREFIX", mock_prefix)
    user_id = get_user_id()
    assert user_id is None
    assert any("not made of five characters" in rec.message for rec in caplog.records)


def test_get_user_id_no_u_prefix(
    monkeypatch: MonkeyPatch, 
    caplog: LogCaptureFixture
) -> None:
    """
    Test get_user_id when the extracted user ID does not start with 'u'.

    Args:
        monkeypatch (MonkeyPatch): Fixture for modifying environment variables safely.
        caplog (LogCaptureFixture): Fixture to capture log outputs.
    """
    mock_prefix = "/notebooks/namespace/x1234-other/edit"
    monkeypatch.setenv("NB_PREFIX", mock_prefix)
    user_id = get_user_id()
    assert user_id is None
    assert any("does not start with 'u'" in rec.message for rec in caplog.records)


def test_get_user_id_index_error(
    monkeypatch: MonkeyPatch, 
    caplog: LogCaptureFixture
) -> None:
    """
    Test get_user_id when NB_PREFIX does not have enough '/' parts.

    Args:
        monkeypatch (MonkeyPatch): Fixture for modifying environment variables safely.
        caplog (LogCaptureFixture): Fixture to capture log outputs.
    """
    mock_prefix = "/not-enough"
    monkeypatch.setenv("NB_PREFIX", mock_prefix)
    user_id = get_user_id()
    assert user_id is None
    assert any("does not contain enough parts" in rec.message for rec in caplog.records)


def test_get_user_id_unexpected_exception(
    monkeypatch: MonkeyPatch, 
    caplog: LogCaptureFixture
) -> None:
    """
    Force an unexpected exception inside get_user_id and check it returns None and logs the exception.

    Args:
        monkeypatch (MonkeyPatch): Fixture for modifying environment variables safely.
        caplog (LogCaptureFixture): Fixture to capture log outputs.
    """
    def mock_split(*args, **kwargs) -> None:
        raise RuntimeError("Unexpected error in split")

    monkeypatch.setenv("NB_PREFIX", "/something/valid-u1234-stuff")
    with patch.object(str, "split", side_effect=mock_split):
        user_id = get_user_id()
        assert user_id is None
        assert any("An error occurred while retrieving the user ID" in rec.message for rec in caplog.records)


# ---------------------------------------------------------------------------
# TESTS for get_db_config
# ---------------------------------------------------------------------------

def test_get_db_config_no_env_uses_local(
    monkeypatch: MonkeyPatch, 
    config_file: Path
) -> None:
    """
    If AEP_ENV is not set, defaults to 'local'.

    Args:
        monkeypatch (MonkeyPatch): Fixture for modifying environment variables safely.
        config_file (Path): Path to a temporary YAML file with valid config data.
    """
    monkeypatch.delenv("AEP_ENV", raising=False)
    with monkeypatch.context() as m:
        # Patch load_config to read our test config
        m.setattr("config_code.load_config", lambda: load_config(str(config_file)))
        from config_code import get_db_config
        db_config = get_db_config()
        assert db_config.environment == Environment.LOCAL
        assert db_config.database == "local_db"
        assert db_config.schema == "public"


@pytest.mark.parametrize("env", ["local", "dev", "staging", "prod"])
def test_get_db_config_valid_env(
    monkeypatch: MonkeyPatch, 
    config_file: Path, 
    env: str
) -> None:
    """
    Test get_db_config for each valid environment in sample_config via parameterization.

    Args:
        monkeypatch (MonkeyPatch): Fixture for modifying environment variables safely.
        config_file (Path): Path to a temporary YAML file with valid config data.
        env (str): One of ["local", "dev", "staging", "prod"].
    """
    monkeypatch.setenv("AEP_ENV", env)
    with monkeypatch.context() as m:
        m.setattr("config_code.load_config", lambda: load_config(str(config_file)))
        from config_code import get_db_config
        db_config = get_db_config()

    assert isinstance(db_config, DBConfig)
    # Check environment
    assert db_config.environment == Environment(env)
    # Check database and schema from sample_config
    if env == "local":
        assert db_config.database == "local_db"
        assert db_config.schema == "public"
    elif env == "dev":
        assert db_config.database == "dev_db"
        assert db_config.schema == "dev_schema"
    elif env == "staging":
        assert db_config.database == "stage_db"
        assert db_config.schema == "stage_schema"
    elif env == "prod":
        assert db_config.database == "prod_db"
        assert db_config.schema == "prod_schema"

    # Check table names
    for required in ["fields", "version", "output"]:
        assert required in db_config.table_names


def test_get_db_config_dev_valid_user(
    monkeypatch: MonkeyPatch, 
    config_file: Path
) -> None:
    """
    Test get_db_config in DEV environment with a valid NB_PREFIX user ID.
    Should prefix the table names with user ID.

    Args:
        monkeypatch (MonkeyPatch): Fixture for modifying environment variables safely.
        config_file (Path): Path to a temporary YAML file with valid config data.
    """
    monkeypatch.setenv("AEP_ENV", "dev")
    monkeypatch.setenv("NB_PREFIX", "/some/path/u5678-xyz/edit")

    with monkeypatch.context() as m:
        m.setattr("config_code.load_config", lambda: load_config(str(config_file)))
        from config_code import get_db_config
        db_config = get_db_config()

    assert db_config.environment == Environment.DEV
    # Table names should be prefixed
    for key, value in db_config.table_names.items():
        assert value.startswith("u5678_")


def test_get_db_config_dev_missing_user(
    monkeypatch: MonkeyPatch, 
    config_file: Path
) -> None:
    """
    Test get_db_config in DEV when NB_PREFIX is invalid, leading to missing user ID.
    Should raise ValueError.

    Args:
        monkeypatch (MonkeyPatch): Fixture for modifying environment variables safely.
        config_file (Path): Path to a temporary YAML file with valid config data.
    """
    monkeypatch.setenv("AEP_ENV", "dev")
    monkeypatch.delenv("NB_PREFIX", raising=False)

    with monkeypatch.context() as m:
        m.setattr("config_code.load_config", lambda: load_config(str(config_file)))
        from config_code import get_db_config
        with pytest.raises(ValueError) as excinfo:
            _ = get_db_config()
        assert "USERID could not be extracted" in str(excinfo.value)


def test_get_db_config_invalid_env(
    monkeypatch: MonkeyPatch, 
    config_file: Path
) -> None:
    """
    Test get_db_config with an invalid AEP_ENV value.
    Should raise ValueError.

    Args:
        monkeypatch (MonkeyPatch): Fixture for modifying environment variables safely.
        config_file (Path): Path to a temporary YAML file with valid config data.
    """
    monkeypatch.setenv("AEP_ENV", "not_a_real_env")
    with monkeypatch.context() as m:
        m.setattr("config_code.load_config", lambda: load_config(str(config_file)))
        from config_code import get_db_config
        with pytest.raises(ValueError) as excinfo:
            _ = get_db_config()
        assert "Invalid environment specified in AEP_ENV" in str(excinfo.value)


def test_get_db_config_missing_env_section(
    monkeypatch: MonkeyPatch, 
    tmp_path: Path
) -> None:
    """
    Test get_db_config when the requested environment is not in the YAML.

    Args:
        monkeypatch (MonkeyPatch): Fixture for modifying environment variables safely.
        tmp_path (Path): A pytest fixture for a unique temporary directory.
    """
    config_data = {
        "local": {
            "database": "local_db",
            "schema": "public",
            "table_names": ["fields_table", "version_table", "output_table"]
        }
        # 'dev' is intentionally missing
    }
    config_path = tmp_path / "missing_env.yaml"
    config_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")

    monkeypatch.setenv("AEP_ENV", "dev")
    with monkeypatch.context() as m:
        from config_code import get_db_config, load_config
        m.setattr("config_code.load_config", lambda: load_config(str(config_path)))
        with pytest.raises(ValueError) as excinfo:
            _ = get_db_config()
        assert "No configuration found for environment: dev" in str(excinfo.value)


def test_get_db_config_missing_required_table_names(
    monkeypatch: MonkeyPatch, 
    tmp_path: Path
) -> None:
    """
    Test get_db_config when the environment config doesn't include all required substrings 
    ('fields', 'version', 'output').

    Args:
        monkeypatch (MonkeyPatch): Fixture for modifying environment variables safely.
        tmp_path (Path): A pytest fixture for a unique temporary directory.
    """
    config_data = {
        "local": {
            "database": "local_db",
            "schema": "public",
            # Missing 'output_table' intentionally
            "table_names": ["fields_table", "version_table"]
        }
    }
    config_path = tmp_path / "incomplete_config.yaml"
    config_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")

    monkeypatch.setenv("AEP_ENV", "local")
    with monkeypatch.context() as m:
        from config_code import get_db_config, load_config
        m.setattr("config_code.load_config", lambda: load_config(str(config_path)))
        with pytest.raises(ValueError) as excinfo:
            _ = get_db_config()
        assert "Missing table names for keys:" in str(excinfo.value)


def test_get_db_config_unrecognized_table_name(
    monkeypatch: MonkeyPatch, 
    tmp_path: Path, 
    caplog: LogCaptureFixture
) -> None:
    """
    Test environment config has a table name that doesn't match any recognized substrings.

    Args:
        monkeypatch (MonkeyPatch): Fixture for modifying environment variables safely.
        tmp_path (Path): A pytest fixture for a unique temporary directory.
        caplog (LogCaptureFixture): Fixture to capture log outputs.
    """
    config_data = {
        "local": {
            "database": "local_db",
            "schema": "public",
            "table_names": [
                "fields_table",
                "version_table",
                "weird_table"  # unrecognized
            ]
        }
    }
    config_path = tmp_path / "unrecognized.yaml"
    config_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")

    monkeypatch.setenv("AEP_ENV", "local")
    with monkeypatch.context() as m:
        from config_code import get_db_config, load_config
        m.setattr("config_code.load_config", lambda: load_config(str(config_path)))
        with pytest.raises(ValueError) as excinfo:
            _ = get_db_config()

        # Should raise error for missing "output", but we also expect a log
        # about "Unrecognized table name: weird_table"
        assert "Missing table names for keys:" in str(excinfo.value)
        assert any("Unrecognized table name: weird_table" in rec.message for rec in caplog.records)


def test_get_db_config_empty_table_list(
    monkeypatch: MonkeyPatch, 
    tmp_path: Path
) -> None:
    """
    Test environment config with an empty table_names list.

    Args:
        monkeypatch (MonkeyPatch): Fixture for modifying environment variables safely.
        tmp_path (Path): A pytest fixture for a unique temporary directory.
    """
    config_data = {
        "local": {
            "database": "local_db",
            "schema": "public",
            "table_names": []
        }
    }
    config_path = tmp_path / "empty_table_list.yaml"
    config_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")

    monkeypatch.setenv("AEP_ENV", "local")
    with monkeypatch.context() as m:
        from config_code import get_db_config, load_config
        m.setattr("config_code.load_config", lambda: load_config(str(config_path)))
        with pytest.raises(ValueError) as excinfo:
            _ = get_db_config()
        assert "Missing table names for keys:" in str(excinfo.value)


def test_get_db_config_multiple_matching_substrings(
    monkeypatch: MonkeyPatch, 
    tmp_path: Path, 
    caplog: LogCaptureFixture
) -> None:
    """
    If the config has multiple table names that match the same substring, 
    it will overwrite. We check if the final dictionary is overwritten with the last match.

    Args:
        monkeypatch (MonkeyPatch): Fixture for modifying environment variables safely.
        tmp_path (Path): A pytest fixture for a unique temporary directory.
        caplog (LogCaptureFixture): Fixture to capture log outputs.
    """
    config_data = {
        "local": {
            "database": "local_db",
            "schema": "public",
            "table_names": [
                "fields_table",
                "fields_extra_table",  # Another 'fields' substring
                "version_table",
                "output_table"
            ]
        }
    }
    config_path = tmp_path / "multiple_substrings.yaml"
    config_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")

    monkeypatch.setenv("AEP_ENV", "local")
    with monkeypatch.context() as m:
        from config_code import get_db_config, load_config
        m.setattr("config_code.load_config", lambda: load_config(str(config_path)))
        db_config = get_db_config()
    
    # The code doesn't raise an error; it simply overwrites 'fields' with the last match.
    assert db_config.table_names["fields"] == "fields_extra_table"
    assert db_config.table_names["version"] == "version_table"
    assert db_config.table_names["output"] == "output_table"


def test_get_db_config_missing_database_or_schema(
    monkeypatch: MonkeyPatch, 
    tmp_path: Path
) -> None:
    """
    If the config is missing 'database' or 'schema', the code uses default ''.
    We verify that no error is raised but the final DBConfig has empty strings.

    Args:
        monkeypatch (MonkeyPatch): Fixture for modifying environment variables safely.
        tmp_path (Path): A pytest fixture for a unique temporary directory.
    """
    config_data = {
        "local": {
            # "database" is missing
            # "schema" is missing
            "table_names": [
                "fields_table",
                "version_table",
                "output_table"
            ]
        }
    }
    config_path = tmp_path / "missing_db_schema.yaml"
    config_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")

    monkeypatch.setenv("AEP_ENV", "local")
    with monkeypatch.context() as m:
        from config_code import get_db_config, load_config
        m.setattr("config_code.load_config", lambda: load_config(str(config_path)))
        db_config = get_db_config()

    assert db_config.database == ""
    assert db_config.schema == ""
    # Table names should still be recognized
    assert db_config.table_names["fields"] == "fields_table"
    assert db_config.table_names["version"] == "version_table"
    assert db_config.table_names["output"] == "output_table"