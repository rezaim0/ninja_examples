# utils.py

from typing import List, Dict
from config import get_db_config
from loguru import logger

BASE_TABLE_NAMES: List[str] = [
    "modelops_docato_fields",
    "modelops_docato_output",
    "modelops_docato_version"
]

def get_physical_table_name(base_name: str) -> str:
    """
    Returns the physical table name corresponding to the given base name,
    considering environment-specific modifications and ensuring the order
    matches between base and physical table names.

    Args:
        base_name (str): The base name of the table as defined in the application.

    Returns:
        str: The physical table name to be used in database queries.

    Raises:
        TypeError: If db_config.table_names is not a list.
        ValueError: If there's a mismatch between base and physical table names.
        ValueError: If the base table name is not found in the mapping.
    """
    db_config = get_db_config()
    # Get the table names from the config.yaml
    physical_table_names: List[str] = db_config.table_names

    # Validate that physical_table_names is a list
    if not isinstance(physical_table_names, list):
        logger.error("db_config.table_names must be a list.")
        raise TypeError("db_config.table_names must be a list.")

    # Validate that lengths match
    if len(BASE_TABLE_NAMES) != len(physical_table_names):
        logger.error(
            f"Mismatch in number of table names: "
            f"{len(BASE_TABLE_NAMES)} base names vs "
            f"{len(physical_table_names)} physical names."
        )
        raise ValueError(
            "Mismatch between the number of base and physical table names. "
            "Ensure they have the same number of elements."
        )

    # Validate that the order matches
    mismatched_indices = []
    for index, (base_name_item, physical_name) in enumerate(zip(BASE_TABLE_NAMES, physical_table_names)):
        # In dev environment, physical names may have a user ID prefix
        if not physical_name.endswith(base_name_item):
            mismatched_indices.append((index, base_name_item, physical_name))

    if mismatched_indices:
        for index, base_name_item, physical_name in mismatched_indices:
            logger.error(
                f"At index {index}: physical table name '{physical_name}' does not match "
                f"base table name '{base_name_item}'."
            )
        raise ValueError("Order of base and physical table names does not match.")

    # Create the mapping
    table_name_mapping: Dict[str, str] = dict(zip(BASE_TABLE_NAMES, physical_table_names))

    # Retrieve the physical table name
    try:
        physical_table_name = table_name_mapping[base_name]
        logger.debug(f"Physical table name for '{base_name}': '{physical_table_name}'")
        return physical_table_name
    except KeyError:
        logger.error(f"Base table name '{base_name}' not found in mapping.")
        raise ValueError(f"Base table name '{base_name}' not found in mapping.")
