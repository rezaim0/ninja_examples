
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
        m.setattr("config_code.load_config", lambda: load_config(str(config_file)))
        db_config = get_db_config()  # Now returns a DBConfig object
        assert isinstance(db_config, DBConfig)
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
        db_config = get_db_config()

    assert isinstance(db_config, DBConfig)
    # Check environment
    assert db_config.environment == Environment(env)

    # Check database & schema from sample_config
    env_data = load_config(str(config_file))[env]
    assert db_config.database == env_data["database"]
    assert db_config.schema == env_data["schema"]

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
        db_config = get_db_config()

    assert db_config.environment == Environment.DEV
    # Verify prefix
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
            "table_names": {
                "fields": "fields_table",
                "version": "version_table",
                "output": "output_table"
            }
        }
        # 'dev' is intentionally missing
    }
    config_path = tmp_path / "missing_env.yaml"
    config_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")

    monkeypatch.setenv("AEP_ENV", "dev")
    with monkeypatch.context() as m:
        m.setattr("config_code.load_config", lambda: load_config(str(config_path)))
        with pytest.raises(ValueError) as excinfo:
            _ = get_db_config()
        assert "No configuration found for environment: dev" in str(excinfo.value)


def test_get_db_config_missing_required_table_names(
    monkeypatch: MonkeyPatch, 
    tmp_path: Path
) -> None:
    """
    Test get_db_config when the environment config doesn't include all required
    table name keys ('fields', 'version', 'output').

    Args:
        monkeypatch (MonkeyPatch): Fixture for modifying environment variables safely.
        tmp_path (Path): A pytest fixture for a unique temporary directory.
    """
    # Missing "output"
    config_data = {
        "local": {
            "database": "local_db",
            "schema": "public",
            "table_names": {
                "fields": "fields_table",
                "version": "version_table"
            }
        }
    }
    config_path = tmp_path / "incomplete_config.yaml"
    config_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")

    monkeypatch.setenv("AEP_ENV", "local")
    with monkeypatch.context() as m:
        m.setattr("config_code.load_config", lambda: load_config(str(config_path)))
        with pytest.raises(ValueError) as excinfo:
            _ = get_db_config()
        assert "Missing table names for keys:" in str(excinfo.value)


def test_get_db_config_extra_keys_warn(
    monkeypatch: MonkeyPatch, 
    tmp_path: Path, 
    caplog: LogCaptureFixture
) -> None:
    """
    Test environment config with extra/unrecognized table name keys; 
    code should log a warning but still proceed.

    Args:
        monkeypatch (MonkeyPatch): Fixture for modifying environment variables safely.
        tmp_path (Path): A pytest fixture for a unique temporary directory.
        caplog (LogCaptureFixture): Fixture to capture log outputs.
    """
    config_data = {
        "local": {
            "database": "local_db",
            "schema": "public",
            "table_names": {
                "fields": "fields_table",
                "version": "version_table",
                "output": "output_table",
                "weird": "some_other_table"   # extra key
            }
        }
    }
    config_path = tmp_path / "extra_keys.yaml"
    config_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")

    monkeypatch.setenv("AEP_ENV", "local")
    with monkeypatch.context() as m:
        m.setattr("config_code.load_config", lambda: load_config(str(config_path)))
        db_config = get_db_config()
        
    # Should log a warning about extra keys, but not fail
    assert db_config.environment == Environment.LOCAL
    assert db_config.table_names["fields"] == "fields_table"
    assert db_config.table_names["version"] == "version_table"
    assert db_config.table_names["output"] == "output_table"
    assert any("Unrecognized extra table name keys" in rec.message for rec in caplog.records)


def test_get_db_config_empty_table_dict(
    monkeypatch: MonkeyPatch, 
    tmp_path: Path
) -> None:
    """
    Test environment config with an empty table_names dictionary.

    Args:
        monkeypatch (MonkeyPatch): Fixture for modifying environment variables safely.
        tmp_path (Path): A pytest fixture for a unique temporary directory.
    """
    config_data = {
        "local": {
            "database": "local_db",
            "schema": "public",
            "table_names": {}
        }
    }
    config_path = tmp_path / "empty_table_dict.yaml"
    config_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")

    monkeypatch.setenv("AEP_ENV", "local")
    with monkeypatch.context() as m:
        m.setattr("config_code.load_config", lambda: load_config(str(config_path)))
        with pytest.raises(ValueError) as excinfo:
            _ = get_db_config()
        assert "Missing table names for keys:" in str(excinfo.value)


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
            "table_names": {
                "fields": "fields_table",
                "version": "version_table",
                "output": "output_table"
            }
        }
    }
    config_path = tmp_path / "missing_db_schema.yaml"
    config_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")

    monkeypatch.setenv("AEP_ENV", "local")
    with monkeypatch.context() as m:
        m.setattr("config_code.load_config", lambda: load_config(str(config_path)))
        db_config = get_db_config()

    assert db_config.database == ""
    assert db_config.schema == ""
    assert db_config.table_names["fields"] == "fields_table"
    assert db_config.table_names["version"] == "version_table"
    assert db_config.table_names["output"] == "output_table"