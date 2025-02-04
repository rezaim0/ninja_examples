import os
import copy
import pytest
import yaml
from pathlib import Path
from typing import Any, Dict, Generator, Callable, Optional
from unittest.mock import patch

from _pytest.logging import LogCaptureFixture
from _pytest.monkeypatch import MonkeyPatch

from config_code import (
    load_config,
    get_user_id,
    get_db_config,
    DBConfig,
    Environment
)


# ------------------------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------------------------

@pytest.fixture
def sample_config() -> Dict[str, Dict[str, Any]]:
    """Provides the base configuration dictionary for all environments.

    Returns:
        Dict[str, Dict[str, Any]]: A dictionary mapping environment names to their configuration.
    """
    return {
        "local": {
            "database": "local_db",
            "schema": "public",
            "table_names": {
                "fields": "fields_table",
                "version": "version_table",
                "output": "output_table"
            }
        },
        "dev": {
            "database": "dev_db",
            "schema": "dev_schema",
            "table_names": {
                "fields": "fields_dev_table",
                "version": "version_dev_table",
                "output": "output_dev_table"
            }
        },
        "staging": {
            "database": "stage_db",
            "schema": "stage_schema",
            "table_names": {
                "fields": "fields_staging_table",
                "version": "version_staging_table",
                "output": "output_staging_table"
            }
        },
        "prod": {
            "database": "prod_db",
            "schema": "prod_schema",
            "table_names": {
                "fields": "fields_prod_table",
                "version": "version_prod_table",
                "output": "output_prod_table"
            }
        }
    }


@pytest.fixture
def config_file(tmp_path: Path, sample_config: Dict[str, Dict[str, Any]]
                ) -> Generator[Path, None, None]:
    """Writes the sample configuration to a temporary YAML file.

    Args:
        tmp_path (Path): A temporary directory provided by pytest.
        sample_config (Dict[str, Dict[str, Any]]): The base configuration.

    Yields:
        Path: The path to the temporary YAML configuration file.
    """
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(sample_config, f)
    yield config_path


@pytest.fixture
def config_factory(sample_config: Dict[str, Dict[str, Any]]
                   ) -> Callable[[Optional[Callable[[Dict[str, Dict[str, Any]]], None]], Dict[str, Dict[str, Any]]]:
    """Returns a factory function to create modified configuration dictionaries.

    The returned factory starts with a deep copy of the base `sample_config` and applies
    an optional modifier callable to produce a variant configuration.

    Args:
        sample_config (Dict[str, Dict[str, Any]]): The base configuration.

    Returns:
        Callable: A factory function that accepts an optional modifier function. The modifier
            receives the deep-copied configuration and can update it in place.
    
    Example:
        def remove_dev(conf: Dict[str, Dict[str, Any]]) -> None:
            conf.pop("dev", None)
        modified_config = config_factory(remove_dev)
    """
    def _factory(
        modifier: Optional[Callable[[Dict[str, Dict[str, Any]]], None]] = None
    ) -> Dict[str, Dict[str, Any]]:
        conf = copy.deepcopy(sample_config)
        if modifier:
            modifier(conf)
        return conf
    return _factory


def write_config(tmp_path: Path, config: Dict[str, Any],
                 filename: str = "test_config.yaml") -> Path:
    """Writes a given configuration dictionary to a YAML file.

    Args:
        tmp_path (Path): The temporary directory path.
        config (Dict[str, Any]): The configuration dictionary to write.
        filename (str, optional): The name of the YAML file. Defaults to "test_config.yaml".

    Returns:
        Path: The path to the written YAML file.
    """
    config_path = tmp_path / filename
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f)
    return config_path


def compute_expected_db_config(
    config: Dict[str, Dict[str, Any]],
    env: str,
    user_id: Optional[str] = None
) -> DBConfig:
    """Computes the expected DBConfig for a given environment based on the configuration.

    In the 'dev' environment, if a valid user_id is provided, the table names are prefixed
    with the user id plus an underscore.

    Args:
        config (Dict[str, Dict[str, Any]]): The configuration dictionary.
        env (str): The target environment (e.g., "local", "dev", "staging", "prod").
        user_id (Optional[str], optional): A valid user id for the 'dev' environment. Defaults to None.

    Raises:
        ValueError: If the specified environment is not found in the configuration.

    Returns:
        DBConfig: The expected database configuration.
    """
    if env not in config:
        raise ValueError(f"Configuration for environment '{env}' not found.")
    env_conf = config[env]
    table_names = env_conf["table_names"].copy()
    if env == "dev" and user_id:
        table_names = {k: f"{user_id}_{v}" for k, v in table_names.items()}
    return DBConfig(
        environment=Environment(env),
        database=env_conf["database"],
        schema=env_conf["schema"],
        table_names=table_names
    )


# ------------------------------------------------------------------------------
# TESTS for load_config
# ------------------------------------------------------------------------------

def test_load_config_success(config_file: Path) -> None:
    """Verifies that a valid YAML file is loaded as a dictionary containing expected environments.

    Args:
        config_file (Path): Path to a valid temporary YAML configuration file.
    """
    config = load_config(config_path=str(config_file))
    assert isinstance(config, dict)
    for env in ["local", "dev", "staging", "prod"]:
        assert env in config


def test_load_config_missing_file(tmp_path: Path) -> None:
    """Verifies that load_config raises FileNotFoundError when the file does not exist.

    Args:
        tmp_path (Path): A temporary directory provided by pytest.
    """
    fake_path = tmp_path / "non_existent.yaml"
    with pytest.raises(FileNotFoundError):
        load_config(config_path=str(fake_path))


def test_load_config_invalid_yaml(tmp_path: Path) -> None:
    """Verifies that load_config raises an exception when the file contains invalid YAML.

    Args:
        tmp_path (Path): A temporary directory provided by pytest.
    """
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("::: not valid yaml :::", encoding="utf-8")
    with pytest.raises(Exception) as excinfo:
        load_config(config_path=str(bad_file))
    assert "could not" in str(excinfo.value).lower() or "yaml" in str(excinfo.value).lower()


# ------------------------------------------------------------------------------
# TESTS for get_user_id
# ------------------------------------------------------------------------------

def test_get_user_id_valid(monkeypatch: MonkeyPatch) -> None:
    """Tests that get_user_id extracts the user id when NB_PREFIX is valid.

    Args:
        monkeypatch (MonkeyPatch): Fixture for safely modifying environment variables.
    """
    monkeypatch.setenv("NB_PREFIX", "/notebooks/namespace/u1234-abc/edit")
    user_id = get_user_id()
    assert user_id == "u1234"


def test_get_user_id_no_env(monkeypatch: MonkeyPatch, caplog: LogCaptureFixture) -> None:
    """Tests that get_user_id returns None and logs a message when NB_PREFIX is not set.

    Args:
        monkeypatch (MonkeyPatch): Fixture for safely modifying environment variables.
        caplog (LogCaptureFixture): Fixture for capturing log output.
    """
    monkeypatch.delenv("NB_PREFIX", raising=False)
    user_id = get_user_id()
    assert user_id is None
    assert any("NB_PREFIX environment variable is not set" in rec.message for rec in caplog.records)


def test_get_user_id_wrong_length(monkeypatch: MonkeyPatch, caplog: LogCaptureFixture) -> None:
    """Tests that get_user_id returns None if the extracted user id is not 5 characters long.

    Args:
        monkeypatch (MonkeyPatch): Fixture for safely modifying environment variables.
        caplog (LogCaptureFixture): Fixture for capturing log output.
    """
    monkeypatch.setenv("NB_PREFIX", "/path/u123456-other")
    user_id = get_user_id()
    assert user_id is None
    assert any("not made of five characters" in rec.message for rec in caplog.records)


def test_get_user_id_no_u_prefix(monkeypatch: MonkeyPatch, caplog: LogCaptureFixture) -> None:
    """Tests that get_user_id returns None if the extracted user id does not start with 'u'.

    Args:
        monkeypatch (MonkeyPatch): Fixture for safely modifying environment variables.
        caplog (LogCaptureFixture): Fixture for capturing log output.
    """
    monkeypatch.setenv("NB_PREFIX", "/notebooks/namespace/x1234-other/edit")
    user_id = get_user_id()
    assert user_id is None
    assert any("does not start with 'u'" in rec.message for rec in caplog.records)


def test_get_user_id_index_error(monkeypatch: MonkeyPatch, caplog: LogCaptureFixture) -> None:
    """Tests that get_user_id returns None if NB_PREFIX does not contain enough parts.

    Args:
        monkeypatch (MonkeyPatch): Fixture for safely modifying environment variables.
        caplog (LogCaptureFixture): Fixture for capturing log output.
    """
    monkeypatch.setenv("NB_PREFIX", "/not-enough")
    user_id = get_user_id()
    assert user_id is None
    assert any("does not contain enough parts" in rec.message for rec in caplog.records)


def test_get_user_id_unexpected_exception(monkeypatch: MonkeyPatch, caplog: LogCaptureFixture) -> None:
    """Tests that get_user_id returns None and logs an error when an unexpected exception occurs.

    Args:
        monkeypatch (MonkeyPatch): Fixture for safely modifying environment variables.
        caplog (LogCaptureFixture): Fixture for capturing log output.
    """
    def mock_split(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("Unexpected error in split")
    monkeypatch.setenv("NB_PREFIX", "/something/valid-u1234-stuff")
    with patch.object(str, "split", side_effect=mock_split):
        user_id = get_user_id()
        assert user_id is None
        assert any("An error occurred while retrieving the user ID" in rec.message for rec in caplog.records)


# ------------------------------------------------------------------------------
# TESTS for get_db_config
# ------------------------------------------------------------------------------

def test_get_db_config_no_env_uses_local(
    monkeypatch: MonkeyPatch,
    config_file: Path,
    sample_config: Dict[str, Dict[str, Any]]
) -> None:
    """Tests that get_db_config defaults to 'local' when AEP_ENV is not set.

    Args:
        monkeypatch (MonkeyPatch): Fixture for safely modifying environment variables.
        config_file (Path): Path to a temporary YAML configuration file.
        sample_config (Dict[str, Dict[str, Any]]): The base configuration.
    """
    monkeypatch.delenv("AEP_ENV", raising=False)
    monkeypatch.setattr("config_code.load_config", lambda: load_config(str(config_file)))
    db_config = get_db_config()
    expected_config = compute_expected_db_config(sample_config, "local")
    assert isinstance(db_config, DBConfig)
    assert db_config.environment == expected_config.environment
    assert db_config.database == expected_config.database
    assert db_config.schema == expected_config.schema
    assert db_config.table_names == expected_config.table_names


@pytest.mark.parametrize("env", ["local", "dev", "staging", "prod"])
def test_get_db_config_valid_env(
    monkeypatch: MonkeyPatch,
    config_file: Path,
    sample_config: Dict[str, Dict[str, Any]],
    env: str
) -> None:
    """Tests get_db_config for each valid environment.

    Args:
        monkeypatch (MonkeyPatch): Fixture for safely modifying environment variables.
        config_file (Path): Path to a temporary YAML configuration file.
        sample_config (Dict[str, Dict[str, Any]]): The base configuration.
        env (str): One of "local", "dev", "staging", "prod".
    """
    monkeypatch.setenv("AEP_ENV", env)
    monkeypatch.setattr("config_code.load_config", lambda: load_config(str(config_file)))
    db_config = get_db_config()
    expected_config = compute_expected_db_config(sample_config, env)
    assert isinstance(db_config, DBConfig)
    assert db_config.environment == expected_config.environment
    assert db_config.database == expected_config.database
    assert db_config.schema == expected_config.schema
    for key in ["fields", "version", "output"]:
        assert key in db_config.table_names


def test_get_db_config_dev_valid_user(
    monkeypatch: MonkeyPatch,
    config_file: Path,
    sample_config: Dict[str, Dict[str, Any]]
) -> None:
    """Tests that in the 'dev' environment, valid NB_PREFIX leads to prefixed table names.

    Args:
        monkeypatch (MonkeyPatch): Fixture for safely modifying environment variables.
        config_file (Path): Path to a temporary YAML configuration file.
        sample_config (Dict[str, Dict[str, Any]]): The base configuration.
    """
    monkeypatch.setenv("AEP_ENV", "dev")
    valid_user = "u5678"
    monkeypatch.setenv("NB_PREFIX", f"/some/path/{valid_user}-xyz/edit")
    monkeypatch.setattr("config_code.load_config", lambda: load_config(str(config_file)))
    db_config = get_db_config()
    expected_config = compute_expected_db_config(sample_config, "dev", user_id=valid_user)
    assert db_config.environment == expected_config.environment
    assert db_config.database == expected_config.database
    assert db_config.schema == expected_config.schema
    assert db_config.table_names == expected_config.table_names


def test_get_db_config_dev_missing_user(monkeypatch: MonkeyPatch, config_file: Path) -> None:
    """Tests that get_db_config raises ValueError in 'dev' if NB_PREFIX is missing.

    Args:
        monkeypatch (MonkeyPatch): Fixture for safely modifying environment variables.
        config_file (Path): Path to a temporary YAML configuration file.
    """
    monkeypatch.setenv("AEP_ENV", "dev")
    monkeypatch.delenv("NB_PREFIX", raising=False)
    monkeypatch.setattr("config_code.load_config", lambda: load_config(str(config_file)))
    with pytest.raises(ValueError) as excinfo:
        _ = get_db_config()
    assert "USERID could not be extracted" in str(excinfo.value)


def test_get_db_config_invalid_env(monkeypatch: MonkeyPatch, config_file: Path) -> None:
    """Tests that get_db_config raises ValueError for an invalid environment.

    Args:
        monkeypatch (MonkeyPatch): Fixture for safely modifying environment variables.
        config_file (Path): Path to a temporary YAML configuration file.
    """
    monkeypatch.setenv("AEP_ENV", "not_a_real_env")
    monkeypatch.setattr("config_code.load_config", lambda: load_config(str(config_file)))
    with pytest.raises(ValueError) as excinfo:
        _ = get_db_config()
    assert "Invalid environment specified in AEP_ENV" in str(excinfo.value)


def test_get_db_config_missing_env_section(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    config_factory: Callable[[Optional[Callable[[Dict[str, Dict[str, Any]]], None]], Dict[str, Dict[str, Any]]]
) -> None:
    """Tests that get_db_config raises ValueError when the requested environment section is missing.

    Args:
        monkeypatch (MonkeyPatch): Fixture for safely modifying environment variables.
        tmp_path (Path): A temporary directory provided by pytest.
        config_factory (Callable): Factory to produce modified configuration dictionaries.
    """
    # Remove the 'dev' environment.
    modified_config = config_factory(lambda conf: conf.pop("dev", None))
    config_path = write_config(tmp_path, modified_config, filename="missing_env.yaml")
    monkeypatch.setenv("AEP_ENV", "dev")
    monkeypatch.setattr("config_code.load_config", lambda: load_config(str(config_path)))
    with pytest.raises(ValueError) as excinfo:
        _ = get_db_config()
    assert "No configuration found for environment: dev" in str(excinfo.value)


def test_get_db_config_missing_env_keys(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    config_factory: Callable[[Optional[Callable[[Dict[str, Dict[str, Any]]], None]], Dict[str, Dict[str, Any]]]
) -> None:
    """Tests that get_db_config raises ValueError when required keys are missing in the environment config.

    Args:
        monkeypatch (MonkeyPatch): Fixture for safely modifying environment variables.
        tmp_path (Path): A temporary directory provided by pytest.
        config_factory (Callable): Factory to produce modified configuration dictionaries.
    """
    # Remove 'database' and 'schema' keys from the local environment.
    def remove_keys(conf: Dict[str, Dict[str, Any]]) -> None:
        conf["local"].pop("database", None)
        conf["local"].pop("schema", None)
    modified_config = config_factory(remove_keys)
    config_path = write_config(tmp_path, modified_config, filename="missing_env_keys.yaml")
    monkeypatch.setenv("AEP_ENV", "local")
    monkeypatch.setattr("config_code.load_config", lambda: load_config(str(config_path)))
    with pytest.raises(ValueError) as excinfo:
        _ = get_db_config()
    assert "Missing required key" in str(excinfo.value)


def test_get_db_config_non_dict_table_names(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    config_factory: Callable[[Optional[Callable[[Dict[str, Dict[str, Any]]], None]], Dict[str, Dict[str, Any]]]
) -> None:
    """Tests that get_db_config raises ValueError when 'table_names' is not a dictionary.

    Args:
        monkeypatch (MonkeyPatch): Fixture for safely modifying environment variables.
        tmp_path (Path): A temporary directory provided by pytest.
        config_factory (Callable): Factory to produce modified configuration dictionaries.
    """
    modified_config = config_factory(lambda conf: conf["local"].update({"table_names": "not_a_dict"}))
    config_path = write_config(tmp_path, modified_config, filename="non_dict_table.yaml")
    monkeypatch.setenv("AEP_ENV", "local")
    monkeypatch.setattr("config_code.load_config", lambda: load_config(str(config_path)))
    with pytest.raises(ValueError) as excinfo:
        _ = get_db_config()
    assert "'table_names' must be a dictionary" in str(excinfo.value)


def test_get_db_config_missing_required_table_keys(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    config_factory: Callable[[Optional[Callable[[Dict[str, Dict[str, Any]]], None]], Dict[str, Dict[str, Any]]]
) -> None:
    """Tests that get_db_config raises ValueError when required keys in 'table_names' are missing.

    Args:
        monkeypatch (MonkeyPatch): Fixture for safely modifying environment variables.
        tmp_path (Path): A temporary directory provided by pytest.
        config_factory (Callable): Factory to produce modified configuration dictionaries.
    """
    modified_config = config_factory(lambda conf: conf["local"]["table_names"].pop("output", None))
    config_path = write_config(tmp_path, modified_config, filename="incomplete_table_keys.yaml")
    monkeypatch.setenv("AEP_ENV", "local")
    monkeypatch.setattr("config_code.load_config", lambda: load_config(str(config_path)))
    with pytest.raises(ValueError) as excinfo:
        _ = get_db_config()
    assert "Missing table names for keys:" in str(excinfo.value)


def test_get_db_config_extra_table_keys(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    config_factory: Callable[[Optional[Callable[[Dict[str, Dict[str, Any]]], None]], Dict[str, Dict[str, Any]]],
    caplog: LogCaptureFixture
) -> None:
    """Tests that get_db_config ignores extra keys in 'table_names' (with a warning).

    Args:
        monkeypatch (MonkeyPatch): Fixture for safely modifying environment variables.
        tmp_path (Path): A temporary directory provided by pytest.
        config_factory (Callable): Factory to produce modified configuration dictionaries.
        caplog (LogCaptureFixture): Fixture for capturing log output.
    """
    modified_config = config_factory(lambda conf: conf["local"]["table_names"].update({"unexpected": "extra_table"}))
    config_path = write_config(tmp_path, modified_config, filename="extra_table_keys.yaml")
    monkeypatch.setenv("AEP_ENV", "local")
    monkeypatch.setattr("config_code.load_config", lambda: load_config(str(config_path)))
    db_config = get_db_config()
    
    # Compute the expected config based on the modified configuration.
    expected_config = compute_expected_db_config({"local": modified_config["local"]}, "local")
    assert db_config.environment == expected_config.environment
    assert db_config.table_names == expected_config.table_names
    assert any("Unrecognized extra table name keys" in rec.message for rec in caplog.records)