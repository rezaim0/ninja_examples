
# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_config():
    """
    Returns a dictionary that mimics a typical YAML config structure 
    for multiple environments.
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
def config_file(tmp_path, sample_config):
    """
    Creates a temporary config file from the sample_config fixture.
    Yields the path to that file.
    """
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(sample_config, f)
    yield config_path


# ---------------------------------------------------------------------------
# TESTS for load_config
# ---------------------------------------------------------------------------

def test_load_config_success(config_file):
    """
    Test that load_config properly loads valid YAML from a given path.
    """
    config = load_config(config_path=str(config_file))
    assert isinstance(config, dict)
    # We expect 'local', 'dev', 'staging', 'prod' sections
    for env in ["local", "dev", "staging", "prod"]:
        assert env in config


def test_load_config_missing_file(tmp_path):
    """
    Test that load_config raises an error if the file does not exist.
    """
    fake_path = tmp_path / "non_existent.yaml"
    with pytest.raises(FileNotFoundError):
        load_config(config_path=str(fake_path))


def test_load_config_invalid_yaml(tmp_path):
    """
    Test that load_config raises an exception if the file is not valid YAML.
    """
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("::: not valid yaml :::", encoding="utf-8")
    with pytest.raises(Exception) as excinfo:
        load_config(config_path=str(bad_file))
    assert "could not" in str(excinfo.value).lower() or "yaml" in str(excinfo.value).lower()


# ---------------------------------------------------------------------------
# TESTS for get_user_id
# ---------------------------------------------------------------------------

def test_get_user_id_valid(monkeypatch):
    """
    Test get_user_id when NB_PREFIX has a valid format, e.g. /user/foo/u1234/edit
    """
    mock_prefix = "/notebooks/namespace/u1234-abc/edit"
    monkeypatch.setenv("NB_PREFIX", mock_prefix)
    user_id = get_user_id()
    assert user_id == "u1234"


def test_get_user_id_no_env(monkeypatch, caplog):
    """
    Test get_user_id when NB_PREFIX is not set at all.
    Also check the log message.
    """
    monkeypatch.delenv("NB_PREFIX", raising=False)
    user_id = get_user_id()
    assert user_id is None
    assert any("NB_PREFIX environment variable is not set" in rec.message for rec in caplog.records)


def test_get_user_id_wrong_length(monkeypatch, caplog):
    """
    Test get_user_id when the extracted user ID is not 5 chars long.
    """
    mock_prefix = "/path/u123456-other"
    monkeypatch.setenv("NB_PREFIX", mock_prefix)
    user_id = get_user_id()
    assert user_id is None
    assert any("not made of five characters" in rec.message for rec in caplog.records)


def test_get_user_id_no_u_prefix(monkeypatch, caplog):
    """
    Test get_user_id when the extracted user ID does not start with 'u'.
    """
    mock_prefix = "/notebooks/namespace/x1234-other/edit"
    monkeypatch.setenv("NB_PREFIX", mock_prefix)
    user_id = get_user_id()
    assert user_id is None
    assert any("does not start with 'u'" in rec.message for rec in caplog.records)


def test_get_user_id_index_error(monkeypatch, caplog):
    """
    Test get_user_id when NB_PREFIX does not have enough '/' parts.
    """
    mock_prefix = "/not-enough"
    monkeypatch.setenv("NB_PREFIX", mock_prefix)
    user_id = get_user_id()
    assert user_id is None
    assert any("does not contain enough parts" in rec.message for rec in caplog.records)


def test_get_user_id_unexpected_exception(monkeypatch, caplog):
    """
    Force an unexpected exception inside get_user_id and check it returns None and logs the exception.
    """
    def mock_split(*args, **kwargs):
        raise RuntimeError("Unexpected error in split")
    monkeypatch.setenv("NB_PREFIX", "/something/valid-u1234-stuff")
    with patch.object(str, "split", side_effect=mock_split):
        user_id = get_user_id()
        assert user_id is None
        assert any("An error occurred while retrieving the user ID" in rec.message for rec in caplog.records)


# ---------------------------------------------------------------------------
# TESTS for get_db_config
# ---------------------------------------------------------------------------

def test_get_db_config_no_env_uses_local(monkeypatch, config_file):
    """
    If AEP_ENV is not set, defaults to 'local'.
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
def test_get_db_config_valid_env(monkeypatch, config_file, env):
    """
    Test get_db_config for each valid environment in sample_config.
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


def test_get_db_config_dev_valid_user(monkeypatch, config_file):
    """
    Test get_db_config in DEV environment with a valid NB_PREFIX user ID.
    Should prefix the table names with user ID.
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


def test_get_db_config_dev_missing_user(monkeypatch, config_file):
    """
    Test get_db_config in DEV when NB_PREFIX is invalid, leading to missing user ID.
    Should raise ValueError.
    """
    monkeypatch.setenv("AEP_ENV", "dev")
    monkeypatch.delenv("NB_PREFIX", raising=False)

    with monkeypatch.context() as m:
        m.setattr("config_code.load_config", lambda: load_config(str(config_file)))
        from config_code import get_db_config
        with pytest.raises(ValueError) as excinfo:
            _ = get_db_config()
        assert "USERID could not be extracted" in str(excinfo.value)


def test_get_db_config_invalid_env(monkeypatch, config_file):
    """
    Test get_db_config with an invalid AEP_ENV value.
    Should raise ValueError.
    """
    monkeypatch.setenv("AEP_ENV", "not_a_real_env")
    with monkeypatch.context() as m:
        m.setattr("config_code.load_config", lambda: load_config(str(config_file)))
        from config_code import get_db_config
        with pytest.raises(ValueError) as excinfo:
            _ = get_db_config()
        assert "Invalid environment specified in AEP_ENV" in str(excinfo.value)


def test_get_db_config_missing_env_section(monkeypatch, tmp_path):
    """
    Test get_db_config when the requested environment is not in the YAML.
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


def test_get_db_config_missing_required_table_names(monkeypatch, tmp_path):
    """
    Test get_db_config when the environment config doesn't include all required substrings 
    ('fields', 'version', 'output').
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


def test_get_db_config_unrecognized_table_name(monkeypatch, tmp_path, caplog):
    """
    Test environment config has a table name that doesn't match any recognized substrings.
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

        # Should raise error for missing "output" anyway, but we also want to see a log 
        # about "Unrecognized table name: weird_table"
        assert "Missing table names for keys:" in str(excinfo.value)
        assert any("Unrecognized table name: weird_table" in rec.message for rec in caplog.records)


def test_get_db_config_empty_table_list(monkeypatch, tmp_path):
    """
    Test environment config with an empty table_names list.
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


def test_get_db_config_multiple_matching_substrings(monkeypatch, tmp_path, caplog):
    """
    If the config has multiple table names that match the same substring, 
    it will overwrite. We check if the final dictionary is overwritten.
    """
    config_data = {
        "local": {
            "database": "local_db",
            "schema": "public",
            "table_names": [
                "fields_table",
                "fields_extra_table",
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
    
    # The code doesn't raise an error; it will simply overwrite 'fields' key 
    # with the last match. Let's see which one we ended up with:
    # The logic: for name in table_names_list: if "fields" in name.lower(): table_names["fields"] = name
    # So the final name for 'fields' might be "fields_extra_table" if it appears last in the list.
    assert db_config.table_names["fields"] == "fields_extra_table"
    # version, output should remain correct
    assert db_config.table_names["version"] == "version_table"
    assert db_config.table_names["output"] == "output_table"


def test_get_db_config_missing_database_or_schema(monkeypatch, tmp_path):
    """
    If the config is missing 'database' or 'schema', the code uses default ''.
    We verify that no error is raised but the final DBConfig has empty string.
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