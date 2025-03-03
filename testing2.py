import pytest
from typing import List, Dict, Any, Tuple


###############################################################################
# Mock helper functions (to be replaced by your actual implementations)
###############################################################################

def convert_values_to_string(records: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Converts all record values to strings.

    Args:
        records (List[Dict[str, Any]]): A list of dictionaries.

    Returns:
        List[Dict[str, str]]: The same dictionaries but with all values converted to strings.
    """
    if not records:
        return []
    converted = []
    for rec in records:
        converted.append({k: str(v) for k, v in rec.items()})
    return converted


def duplicate_records(record_from_db: Dict[str, Any],
                     record_from_incoming: Dict[str, Any]) -> bool:
    """
    Determines if a database record and an incoming record are considered duplicates.

    For demonstration:
    1) Checks if all fields except "start_dttm" match exactly.
    2) If they do, then compares the 'start_dttm' fields:
       - If they are identical OR the incoming is earlier (lexicographically),
         it is considered a duplicate.

    Args:
        record_from_db (Dict[str, Any]): A single record from the database.
        record_from_incoming (Dict[str, Any]): A single record from the incoming list.

    Returns:
        bool: True if they are duplicates, False otherwise.
    """
    db_copy = dict(record_from_db)
    incoming_copy = dict(record_from_incoming)

    db_start = db_copy.pop('start_dttm', None)
    incoming_start = incoming_copy.pop('start_dttm', None)

    # Check if non-'start_dttm' fields match
    if db_copy == incoming_copy:
        # If times match or incoming time is earlier, consider them duplicates
        if db_start == incoming_start or (incoming_start < db_start):
            return True
    return False


###############################################################################
# Function under test (with type hints and docstring).
# Replace the helper calls with real imports in production code.
###############################################################################
def remove_matching_records(
    list_from_db: List[Dict[str, Any]],
    list_from_incoming: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Identifies and removes records that appear in both lists (DB and incoming).
    A record is considered a duplicate if it is identical in both lists, or if
    the start datetime of the record in the incoming list is earlier than in
    the database list.

    This is determined by the helper function `duplicate_records`.

    Args:
        list_from_db (List[Dict[str, Any]]): A list of records from the database.
        list_from_incoming (List[Dict[str, Any]]): A list of records from incoming data.

    Returns:
        Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
            A tuple of two lists with duplicates removed. The first list
            corresponds to records from the DB with duplicates removed,
            and the second list corresponds to the incoming records with duplicates removed.
    """
    converted_list_from_db = convert_values_to_string(list_from_db) if list_from_db else []
    converted_list_from_incoming = convert_values_to_string(list_from_incoming) if list_from_incoming else []

    if converted_list_from_db:
        cleaned_list_from_db_to_enddate = [
            record_from_db
            for record_from_db in converted_list_from_db
            if not any(
                duplicate_records(
                    record_from_db=record_from_db,
                    record_from_incoming=record_from_incoming,
                )
                for record_from_incoming in converted_list_from_incoming
            )
        ]
    else:
        cleaned_list_from_db_to_enddate = []

    if converted_list_from_incoming:
        cleaned_list_from_incoming_to_update = [
            record_from_incoming
            for record_from_incoming in converted_list_from_incoming
            if not any(
                duplicate_records(
                    record_from_db=record_from_db,
                    record_from_incoming=record_from_incoming,
                )
                for record_from_db in converted_list_from_db
            )
        ]
    else:
        cleaned_list_from_incoming_to_update = []

    return cleaned_list_from_db_to_enddate, cleaned_list_from_incoming_to_update


###############################################################################
# Pytest Test Cases (with type hints and Google-style docstrings)
###############################################################################

def test_remove_matching_records_empty_inputs() -> None:
    """
    Test remove_matching_records with empty input lists.

    Ensures that if both lists are empty, the function returns two empty lists.

    Returns:
        None
    """
    db_list: List[Dict[str, Any]] = []
    incoming_list: List[Dict[str, Any]] = []
    result_db, result_incoming = remove_matching_records(db_list, incoming_list)
    assert result_db == []
    assert result_incoming == []


def test_remove_matching_records_no_duplicates() -> None:
    """
    Test remove_matching_records when there are no matching or duplicate records.

    Both lists should remain essentially unchanged (except for the values being
    converted to strings).

    Returns:
        None
    """
    db_list: List[Dict[str, Any]] = [
        {"id": 1, "name": "Alice", "start_dttm": "2021-01-01"},
        {"id": 2, "name": "Bob",   "start_dttm": "2021-01-02"}
    ]
    incoming_list: List[Dict[str, Any]] = [
        {"id": 3, "name": "Charlie", "start_dttm": "2021-02-01"},
        {"id": 4, "name": "Diana",   "start_dttm": "2021-02-02"}
    ]
    result_db, result_incoming = remove_matching_records(db_list, incoming_list)

    expected_db = [
        {"id": "1", "name": "Alice", "start_dttm": "2021-01-01"},
        {"id": "2", "name": "Bob",   "start_dttm": "2021-01-02"}
    ]
    expected_incoming = [
        {"id": "3", "name": "Charlie", "start_dttm": "2021-02-01"},
        {"id": "4", "name": "Diana",   "start_dttm": "2021-02-02"}
    ]
    assert result_db == expected_db
    assert result_incoming == expected_incoming


def test_remove_matching_records_identical_records() -> None:
    """
    Test remove_matching_records with records that are identical in both lists.

    Identical records should be removed from both lists entirely.

    Returns:
        None
    """
    db_list: List[Dict[str, Any]] = [
        {"id": 1, "name": "Alice", "start_dttm": "2021-01-01"},
        {"id": 2, "name": "Bob",   "start_dttm": "2021-01-02"}
    ]
    incoming_list: List[Dict[str, Any]] = [
        {"id": 1, "name": "Alice", "start_dttm": "2021-01-01"},
        {"id": 3, "name": "Charlie", "start_dttm": "2021-03-01"}
    ]
    result_db, result_incoming = remove_matching_records(db_list, incoming_list)

    # Alice should be removed from both
    expected_db = [
        {"id": "2", "name": "Bob", "start_dttm": "2021-01-02"}
    ]
    expected_incoming = [
        {"id": "3", "name": "Charlie", "start_dttm": "2021-03-01"}
    ]
    assert result_db == expected_db
    assert result_incoming == expected_incoming


def test_remove_matching_records_earlier_incoming() -> None:
    """
    Test remove_matching_records where the incoming record's 'start_dttm' is earlier.

    The records share all other fields, so they are considered duplicates if
    the incoming 'start_dttm' is earlier.

    Returns:
        None
    """
    db_list: List[Dict[str, Any]] = [
        {"id": 1, "name": "Alice", "start_dttm": "2021-01-01"}
    ]
    incoming_list: List[Dict[str, Any]] = [
        {"id": 1, "name": "Alice", "start_dttm": "2020-12-31"}
    ]
    result_db, result_incoming = remove_matching_records(db_list, incoming_list)

    # Both should be removed given the 'earlier_incoming' logic
    assert result_db == []
    assert result_incoming == []


def test_remove_matching_records_no_shared_fields() -> None:
    """
    Test remove_matching_records when the records do not share enough fields to be duplicates.

    The records should remain unchanged except for string conversion.

    Returns:
        None
    """
    db_list: List[Dict[str, Any]] = [{"id": 1, "foo": "bar", "start_dttm": "2021-10-10"}]
    incoming_list: List[Dict[str, Any]] = [{"id2": 99, "name": "X", "start_dttm": "2021-01-01"}]
    result_db, result_incoming = remove_matching_records(db_list, incoming_list)

    expected_db = [{"id": "1", "foo": "bar", "start_dttm": "2021-10-10"}]
    expected_incoming = [{"id2": "99", "name": "X", "start_dttm": "2021-01-01"}]

    assert result_db == expected_db
    assert result_incoming == expected_incoming


def test_remove_matching_records_mixed_scenario() -> None:
    """
    Test remove_matching_records with a mix of matching and non-matching records.

    Includes exact matches, earlier incoming start times, and brand-new records.

    Returns:
        None
    """
    db_list: List[Dict[str, Any]] = [
        {"id": 1, "name": "Alice",  "start_dttm": "2021-01-01"},
        {"id": 2, "name": "Bob",    "start_dttm": "2021-02-01"},
        {"id": 3, "name": "Cathy",  "start_dttm": "2021-03-01"}
    ]
    incoming_list: List[Dict[str, Any]] = [
        {"id": 2, "name": "Bob",    "start_dttm": "2021-02-01"},   # exact match
        {"id": 3, "name": "Cathy",  "start_dttm": "2021-02-25"},   # earlier than 2021-03-01
        {"id": 4, "name": "Dan",    "start_dttm": "2021-04-01"}    # new record
    ]
    result_db, result_incoming = remove_matching_records(db_list, incoming_list)

    # Bob and Cathy should be removed from both, leaving only Alice in DB and Dan incoming
    expected_db = [
        {"id": "1", "name": "Alice", "start_dttm": "2021-01-01"}
    ]
    expected_incoming = [
        {"id": "4", "name": "Dan", "start_dttm": "2021-04-01"}
    ]
    assert result_db == expected_db
    assert result_incoming == expected_incoming