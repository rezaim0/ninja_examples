
@pytest.mark.parametrize("scenario", [
    {
        "name": "both_sql_file_and_flib_modules",
        "args": ["--sql-file", "myquery.sql", "--flib-modules", "mod1"],
        "mock_get_sql_file_paths": None,
        "mock_extract_source_tables": None,
        "expected_exit_code": 1,
        "expected_logs": ["ERROR Please provide either SQL files or module names, but not both."],
        "expected_output": ""
    },
    {
        "name": "no_args",
        "args": [],
        "mock_get_sql_file_paths": None,
        "mock_extract_source_tables": None,
        "expected_exit_code": 1,
        "expected_logs": ["ERROR No SQL files or modules have been provided."],
        "expected_output": ""
    },
    {
        "name": "flib_modules_no_sql_files",
        "args": ["--flib-modules", "mod1"],
        "mock_get_sql_file_paths": {
            "return_value": {}
        },
        "mock_extract_source_tables": None,
        "expected_exit_code": 1,
        "expected_logs": [
            "INFO Fetching SQL files for modules: ['mod1']",
            "ERROR No SQL files found for the specified modules."
        ],
        "expected_output": ""
    },
    {
        "name": "flib_modules_module_not_found_error",
        "args": ["--flib-modules", "mod1"],
        "mock_get_sql_file_paths": {
            "side_effect": ModuleNotFoundError("Base package not found.")
        },
        "mock_extract_source_tables": None,
        "expected_exit_code": 1,
        "expected_logs": [
            "INFO Fetching SQL files for modules: ['mod1']",
            "ERROR Failed to find project modules: Base package not found."
        ],
        "expected_output": ""
    },
    {
        "name": "flib_modules_type_error",
        "args": ["--flib-modules", "mod1"],
        "mock_get_sql_file_paths": {
            "side_effect": TypeError("Invalid input for modules.")
        },
        "mock_extract_source_tables": None,
        "expected_exit_code": 1,
        "expected_logs": [
            "INFO Fetching SQL files for modules: ['mod1']",
            "ERROR Invalid input for modules: Invalid input for modules."
        ],
        "expected_output": ""
    },
    {
        "name": "flib_modules_unexpected_error",
        "args": ["--flib-modules", "mod1"],
        "mock_get_sql_file_paths": {
            "side_effect": Exception("Unknown error")
        },
        "mock_extract_source_tables": None,
        "expected_exit_code": 1,
        "expected_logs": [
            "INFO Fetching SQL files for modules: ['mod1']",
            "ERROR An unexpected error occurred while fetching SQL files: Unknown error"
        ],
        "expected_output": ""
    },
    {
        "name": "flib_modules_success",
        "args": ["--flib-modules", "mod1"],
        "mock_get_sql_file_paths": {
            "return_value": {"mod1": "/path/to/mod1.sql"}
        },
        "mock_extract_source_tables": {
            "return_value": ["tableA", "tableB"]
        },
        "expected_exit_code": 0,
        "expected_logs": [
            "INFO Fetching SQL files for modules: ['mod1']",
            "INFO Source tables have been found."
        ],
        "expected_output": "    - tableA\n    - tableB\n"
    },
    {
        "name": "sql_file_success",
        "args": ["--sql-file", "myquery.sql"],
        "mock_get_sql_file_paths": None,
        "mock_extract_source_tables": {
            "return_value": ["tableC"]
        },
        "expected_exit_code": 0,
        "expected_logs": [
            "INFO Source tables have been found."
        ],
        "expected_output": "    - tableC\n"
    },
    {
        "name": "sql_file_no_tables_found",
        "args": ["--sql-file", "myquery.sql"],
        "mock_extract_source_tables": {
            "return_value": []
        },
        "expected_exit_code": 1,
        "expected_logs": [
            "WARNING No source tables were found in ['myquery.sql']"
        ],
        "expected_output": ""
    },
    {
        "name": "sql_file_file_not_found_error",
        "args": ["--sql-file", "missing.sql"],
        "mock_extract_source_tables": {
            "side_effect": FileNotFoundError("File missing.sql not found.")
        },
        "expected_exit_code": 1,
        "expected_logs": [
            "ERROR SQL file not found: File missing.sql not found."
        ],
        "expected_output": ""
    },
    {
        "name": "sql_file_permission_error",
        "args": ["--sql-file", "secret.sql"],
        "mock_extract_source_tables": {
            "side_effect": PermissionError("No permission to read secret.sql")
        },
        "expected_exit_code": 1,
        "expected_logs": [
            "ERROR Permission error while reading SQL files: No permission to read secret.sql"
        ],
        "expected_output": ""
    },
    {
        "name": "sql_file_unexpected_error",
        "args": ["--sql-file", "broken.sql"],
        "mock_extract_source_tables": {
            "side_effect": Exception("Some unexpected error")
        },
        "expected_exit_code": 1,
        "expected_logs": [
            "ERROR An error occurred while extracting source tables: Some unexpected error"
        ],
        "expected_output": ""
    }
])