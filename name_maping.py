# other_module.py

from config import get_db_config

def main():
    # Retrieve the database configuration
    db_config = get_db_config()
    
    # Define the logical table names
    logical_table_names = [
        "modelops_docato_fields",
        "modelops_docato_output",
        "modelops_docato_version"
    ]
    
    # Get the physical table names from the configuration
    physical_table_names = db_config.table_names
    
    # Create a mapping from logical to physical table names
    table_name_mapping = dict(zip(logical_table_names, physical_table_names))
    
    # Retrieve the physical table name for 'modelops_docato_version'
    logical_name = "modelops_docato_version"
    physical_name = table_name_mapping[logical_name]
    
    # Construct the fully qualified table name
    schema = db_config.schema
    fully_qualified_table_name = f"{schema}.{physical_name}" if schema else physical_name
    
    # Use the table name in your code
    query = f"SELECT * FROM {fully_qualified_table_name};"
    print(f"Executing query: {query}")
    # Here you would execute the query using your database connection

if __name__ == "__main__":
    main()

############################## second method #####################

# utils.py

from config import get_db_config

def get_physical_table_name(logical_name: str) -> str:
    """
    Returns the physical table name corresponding to the given logical name.
    """
    db_config = get_db_config()
    logical_table_names = [
        "modelops_docato_fields",
        "modelops_docato_output",
        "modelops_docato_version"
    ]
    physical_table_names = db_config.table_names
    table_name_mapping = dict(zip(logical_table_names, physical_table_names))
    
    try:
        return table_name_mapping[logical_name]
    except KeyError:
        raise ValueError(f"Logical table name '{logical_name}' not found in configuration.")


# other_module.py

from utils import get_physical_table_name
from config import get_db_config

def main():
    # Retrieve the physical table name for 'modelops_docato_version'
    physical_name = get_physical_table_name("modelops_docato_version")
    
    # Get the schema from db_config
    db_config = get_db_config()
    schema = db_config.schema
    fully_qualified_table_name = f"{schema}.{physical_name}" if schema else physical_name
    
    # Use the table name in your code
    query = f"SELECT * FROM {fully_qualified_table_name};"
    print(f"Executing query: {query}")
    # Execute the query using your database connection

if __name__ == "__main__":
    main()



#########################


# constants.py

LOGICAL_TABLE_NAMES = [
    "modelops_docato_fields",
    "modelops_docato_output",
    "modelops_docato_version"
]


# utils.py

from config import get_db_config
from constants import LOGICAL_TABLE_NAMES

def get_physical_table_name(logical_name: str) -> str:
    db_config = get_db_config()
    physical_table_names = db_config.table_names
    table_name_mapping = dict(zip(LOGICAL_TABLE_NAMES, physical_table_names))
    try:
        return table_name_mapping[logical_name]
    except KeyError:
        raise ValueError(f"Logical table name '{logical_name}' not found in configuration.")


# utils.py

from config import get_db_config
from constants import LOGICAL_TABLE_NAMES  # Assuming you have a constants module

def get_physical_table_name(logical_name: str) -> str:
    """
    Returns the physical table name corresponding to the given logical name.
    """
    db_config = get_db_config()
    physical_table_names = db_config.table_names
    table_name_mapping = dict(zip(LOGICAL_TABLE_NAMES, physical_table_names))
    
    try:
        return table_name_mapping[logical_name]
    except KeyError:
        raise ValueError(f"Logical table name '{logical_name}' not found in configuration.")
