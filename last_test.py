@pytest.mark.parametrize("invalid_table_names,missing_keys", [
    (["modelops_docato_fields", "modelops_docato_output"], {"version"}),
    (["modelops_docato_fields"], {"version", "output"}),
    (["invalid_table_1", "invalid_table_2", "invalid_table_3"], {"fields", "version", "output"}),
])
def test_get_db_config_invalid_table_names(
    mocker: MockerFixture,
    sample_config: Dict[str, Any],
    invalid_table_names: list,
    missing_keys: set
) -> None:
    """
    Tests get_db_config with invalid or missing table names.

    Args:
        mocker (MockerFixture): Pytest mocker fixture.
        sample_config (Dict[str, Any]): Sample configuration data.
        invalid_table_names (list): List of invalid table names to test.
        missing_keys (set): Expected missing keys in the error message.
    """
    sample_config["local"]["table_names"] = invalid_table_names
    
    mocker.patch.dict(os.environ, {"AEP_ENV": "local"})
    mocker.patch("config.load_config", return_value=sample_config)
    
    with pytest.raises(ValueError) as exc_info:
        get_db_config()
    
    # Convert the error message's missing keys string back to a set for comparison
    error_msg = str(exc_info.value)
    actual_missing_keys = set(error_msg.split("Missing table names for keys: ")[1].strip("{}").split(", "))
    assert actual_missing_keys == missing_keys