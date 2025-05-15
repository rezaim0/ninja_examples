import re
from pathlib import Path
from typing import Tuple, List, Set, Optional

# Precompile regex patterns for better performance
BLOCK_COMMENT_PATTERN = re.compile(r"/\*.*?\*/", re.DOTALL | re.IGNORECASE)
LINE_COMMENT_PATTERN = re.compile(r"--[^\n]*", re.IGNORECASE)
SPLIT_RESPECTING_QUOTES = re.compile(r'\s+(?=(?:[^"]*"[^"]*")*[^"]*$)')
CASE_EXPR_START = re.compile(r'\bcase\b', re.IGNORECASE)
CASE_EXPR_END = re.compile(r'\bend\b', re.IGNORECASE)

def _clean_table_name(name_token: str) -> Optional[str]:
    """
    Cleans a potential table name token.
    - Strips common surrounding characters (whitespace, semicolon, comma, parentheses).
    - Handles Teradata double-quoting (e.g., "My Table", "My Schema"."My Table").
    - Handles escaped double quotes within identifiers (e.g., "My ""Special"" Table").
    - Preserves 'Database.Table' or 'Schema.Table' structure.
    - Returns None if the token is empty after cleaning or looks like a common SQL keyword.
    """
    if not name_token:
        return None

    # Strip common SQL delimiters and whitespace from the ends.
    # Dot is intentionally not stripped here as it's part of schema.table.
    cleaned_name = name_token.strip(";,() \t\n\r")

    # Handle Teradata double quotes for identifiers.
    # This logic assumes quotes are either around the entire identifier
    # or around individual parts of a qualified name like "schema"."table".
    
    # First, unescape any Teradata-style escaped double quotes ("") to a single quote (")
    # This makes further processing of quoted identifiers simpler.
    temp_unquoted = cleaned_name.replace('""', '"')

    # If the entire name_token (after initial strip and unescape) is quoted
    if temp_unquoted.startswith('"') and temp_unquoted.endswith('"'):
        # Remove the outer quotes
        core_name = temp_unquoted[1:-1]
    else:
        core_name = temp_unquoted # No surrounding quotes or mixed content

    # At this point, core_name is the identifier string, potentially with internal dots.
    # e.g., MyTable, My Schema.My Table (if original was "My Schema"."My Table")
    # We don't need to further split by '.' and re-quote unless the input format was very specific.
    # The goal is to get the canonical representation.

    final_name = core_name

    # Basic validation: if after cleaning, it's empty or a common keyword, reject.
    # This list can be expanded.
    common_sql_keywords_to_avoid = {
        'as', 'on', 'set', '(', ')', 'select', 'values', 'option', 'constraint',
        'primary', 'key', 'foreign', 'references', 'index', 'unique', 'database',
        'user', 'password', 'role', 'profile', 'account', 'case', 'when', 'then',
        'else', 'end', 'with', 'recursive', 'union', 'all', 'between', 'like',
        'in', 'exists', 'is', 'null', 'not', 'and', 'or', 'distinct', 'top',
        'limit', 'offset', 'order', 'by', 'group', 'having', 'qualify', 'row',
        'rows', 'range', 'over', 'partition', 'unbounded', 'preceding', 'following',
        'current', 'first', 'last', 'only', 'with', 'recursive'
    }
    if not final_name or final_name.lower() in common_sql_keywords_to_avoid:
        return None
    
    # Prevent overly short or purely symbolic names if they slip through.
    if len(final_name) < 1: # Or a more aggressive minimum length if desired
        return None
    if final_name.count('.') > 5: # Arbitrary limit to avoid malformed long dot chains
        return None

    return final_name


class SQLParsingError(Exception):
    """Exception raised for errors during SQL parsing."""
    pass


def find_teradata_tables(file_path: Path) -> Tuple[List[str], List[str]]:
    """
    Extracts source and temporary table names from a Teradata SQL file.

    Args:
        file_path: Path to the SQL file.

    Returns:
        A tuple containing two lists: (source_tables, temp_tables).
        Table names preserve their original casing.
        
    Raises:
        SQLParsingError: If there's an error during SQL parsing.
        FileNotFoundError: If the specified file cannot be found.
        PermissionError: If there's no permission to read the file.
        UnicodeDecodeError: If the file encoding cannot be properly decoded.
    """
    source_tables_set: Set[str] = set()
    temp_tables_set: Set[str] = set()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text_content = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except PermissionError:
        raise PermissionError(f"Permission denied: {file_path}")
    except UnicodeDecodeError:
        # Try with a different encoding
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                text_content = f.read()
        except UnicodeDecodeError:
            raise UnicodeDecodeError("utf-8", b"", 0, 1, 
                                    f"Could not decode file {file_path} with utf-8 or latin-1 encoding")
    except Exception as e:
        raise SQLParsingError(f"Error reading file {file_path}: {e}")

    try:
        # 1. Remove block comments /* ... */
        text_content = BLOCK_COMMENT_PATTERN.sub("", text_content)
        
        # 2. Remove single-line comments -- ...
        text_content = LINE_COMMENT_PATTERN.sub("", text_content)
        
        # 3. Split into statements (Teradata uses semicolon)
        statements = [stmt.strip() for stmt in text_content.split(';') if stmt.strip()]

        # Track CASE/END blocks to avoid misinterpreting table names within expressions
        for stmt in statements:
            # Split by whitespace, respecting quotes
            words = SPLIT_RESPECTING_QUOTES.split(stmt)
            words = [word for word in words if word] # Remove empty strings from split

            if not words:
                continue

            i = 0
            in_case_expr = 0  # Track nesting level of CASE expressions
            
            while i < len(words):
                word_original_case = words[i]
                lower_word = word_original_case.lower()

                # Track CASE/END blocks
                if CASE_EXPR_START.search(lower_word):
                    in_case_expr += 1
                elif CASE_EXPR_END.search(lower_word) and in_case_expr > 0:
                    in_case_expr -= 1
                
                # Skip table name detection within CASE expressions
                if in_case_expr > 0:
                    i += 1
                    continue

                table_candidate = None
                is_temp = False
                consumed_tokens = 1  # How many tokens (words) this rule consumes
                
                # --- WITH Clause for CTEs ---
                if lower_word == "with":
                    # Check if it's a recursive CTE
                    is_recursive = False
                    if i > 0 and words[i-1].lower() == "recursive":
                        is_recursive = True
                    
                    # Save current position to restore if needed
                    original_i = i
                    
                    # Move forward to process CTE names in the WITH clause
                    cte_i = i + (1 if not is_recursive else 0)
                    while cte_i < len(words) - 2:  # Need at least 3 tokens: name AS (...)
                        cte_name_candidate = words[cte_i]
                        
                        # Check if this looks like a valid CTE name followed by AS
                        if cte_i + 1 < len(words) and words[cte_i + 1].lower() == "as":
                            cleaned_cte = _clean_table_name(cte_name_candidate)
                            if cleaned_cte:
                                temp_tables_set.add(cleaned_cte)
                            
                            # Skip past this CTE definition to look for the next one
                            # Find closing parenthesis of CTE definition
                            paren_level = 0
                            found_open = False
                            
                            for j in range(cte_i + 2, len(words)):
                                if "(" in words[j]:
                                    found_open = True
                                    paren_level += words[j].count("(")
                                if ")" in words[j]:
                                    paren_level -= words[j].count(")")
                                
                                if found_open and paren_level <= 0:
                                    # Found the end of this CTE definition
                                    cte_i = j + 1
                                    break
                            else:
                                # If we didn't find the closing parenthesis, move to the next word after AS
                                cte_i += 2
                            
                            # Check if we hit a comma for another CTE or SELECT for the main query
                            if cte_i < len(words):
                                if words[cte_i].strip() == ",":
                                    # Another CTE follows, continue to the next name
                                    cte_i += 1
                                    continue
                                elif words[cte_i].lower() == "select":
                                    # End of WITH clause, main query follows
                                    break
                        else:
                            # Not a CTE pattern, move on
                            cte_i += 1
                    
                    # Update consumed tokens to skip past all CTEs we processed
                    consumed_tokens = cte_i - i
                    
                    # If we didn't consume any tokens, just move to the next word
                    if consumed_tokens <= 0:
                        consumed_tokens = 1

                # --- Temp Tables (Definitions) ---
                elif lower_word == "create":
                    if i + 2 < len(words): # Need at least CREATE TYPE NAME
                        type_word_lower = words[i+1].lower()
                        name_candidate_idx = i + 2
                        
                        if type_word_lower == "view":
                            table_candidate = words[name_candidate_idx]
                            is_temp = True
                            consumed_tokens = 3
                        elif type_word_lower in ["table", "set", "multiset", "volatile", "global"]:
                            # Handles: CREATE TABLE, CREATE SET TABLE, CREATE MULTISET TABLE, CREATE VOLATILE TABLE
                            if type_word_lower in ["set", "multiset", "volatile"]:
                                if i + 3 < len(words) and words[i+2].lower() == "table":
                                    table_candidate = words[i+3]
                                    consumed_tokens = 4
                                # else: it might be "CREATE SET foo" (if SET is a type) - not for tables
                            elif type_word_lower == "global":
                                if i + 4 < len(words) and words[i+2].lower() == "temporary" and words[i+3].lower() == "table":
                                    table_candidate = words[i+4]
                                    consumed_tokens = 5
                                elif i+3 < len(words) and words[i+2].lower() == "table": # CREATE GLOBAL TABLE
                                    table_candidate = words[i+3]
                                    consumed_tokens = 4
                            elif type_word_lower == "table": # CREATE TABLE
                                 table_candidate = words[name_candidate_idx]
                                 consumed_tokens = 3
                            if table_candidate: is_temp = True
                
                # --- Source/Referenced Tables ---
                elif lower_word in ["from", "join", "update", "delete"]:
                    if i + 1 < len(words):
                        # Avoid picking up keywords like "FROM" in "DELETE FROM" if "FROM" is taken as table
                        if words[i+1].lower() not in ["set", "where", "(", "*", "user", "database"]: # Basic filter
                            table_candidate = words[i+1]
                            consumed_tokens = 2
                            # Rudimentary check for comma-separated tables after FROM/JOIN: FROM table1, table2
                            # This only works if table1 ends with a comma or if table1 is clean and next is comma
                            potential_first_table = _clean_table_name(table_candidate)
                            if potential_first_table:
                                source_tables_set.add(potential_first_table)
                            
                            # Check if the cleaned table_candidate itself ended with a comma (now removed by _clean)
                            # or if the *next* token is a comma, then take the one after that.
                            # This is very basic and can be fooled.
                            temp_i = i + consumed_tokens
                            while temp_i < len(words) -1 and words[temp_i].strip() == ',':
                                if temp_i + 1 < len(words):
                                    next_table_in_list = _clean_table_name(words[temp_i+1])
                                    if next_table_in_list:
                                        source_tables_set.add(next_table_in_list)
                                    temp_i += 2 # consumed comma and table
                                    consumed_tokens = (temp_i - i) # update consumed tokens
                                else:
                                    break
                            else: # No comma directly after, or loop ended
                                # If first table was already added, we might not need to do anything here
                                # unless table_candidate was not yet processed.
                                if not potential_first_table and table_candidate: # if first wasn't added
                                    pass # table_candidate will be processed below
                                else: # first table was added, and comma list processed
                                    table_candidate = None # Signal it's handled

                elif lower_word == "into": # INSERT INTO table_name, MERGE INTO table_name
                    if i > 0 and words[i-1].lower() in ["insert", "merge"]:
                        if i + 1 < len(words):
                            table_candidate = words[i+1]
                            consumed_tokens = 2
                    # Could also be SELECT ... INTO :variable (not a table) - _clean_table_name might filter some
                
                elif lower_word == "using": # MERGE ... USING source_table
                    is_merge_context = any(w.lower() == "merge" for w in words[:i])
                    if is_merge_context and i + 1 < len(words):
                        table_candidate = words[i+1]
                        consumed_tokens = 2
                
                elif lower_word == "statistics" and i > 0 and words[i-1].lower() == "collect": # COLLECT STATISTICS ON table_name
                    if i + 2 < len(words) and words[i+1].lower() == "on":
                        table_candidate = words[i+2]
                        consumed_tokens = 3
                
                elif lower_word == "table" and i > 0:
                    prev_word_lower = words[i-1].lower()
                    if prev_word_lower == "locking": # LOCKING TABLE table_name
                        if i + 1 < len(words):
                            table_candidate = words[i+1]
                            consumed_tokens = 2
                    elif prev_word_lower == "rename": # RENAME TABLE old_table_name TO new_table_name
                        if i + 1 < len(words): # old_table_name
                            old_table = _clean_table_name(words[i+1])
                            if old_table: source_tables_set.add(old_table)
                        if i + 3 < len(words) and words[i+2].lower() == "to": # new_table_name
                            new_table = _clean_table_name(words[i+3])
                            if new_table: temp_tables_set.add(new_table) # New name is like a "temp" definition
                            consumed_tokens = 4
                        else: # only processed old name part or malformed
                            consumed_tokens = 2 # at least consumed "RENAME TABLE old_name"
                        table_candidate = None # Handled directly

                # --- Add to sets ---
                if table_candidate:
                    try:
                        cleaned_name = _clean_table_name(table_candidate)
                        if cleaned_name:
                            if is_temp:
                                temp_tables_set.add(cleaned_name)
                            else:
                                source_tables_set.add(cleaned_name)
                    except Exception as e:
                        # Log error but continue processing
                        print(f"Error processing table candidate '{table_candidate}': {e}")
                
                i += consumed_tokens
                
        return sorted(list(source_tables_set)), sorted(list(temp_tables_set))
    
    except Exception as e:
        raise SQLParsingError(f"Error parsing SQL in file {file_path}: {e}")


# --------------------------------------

import pytest
from pathlib import Path
import tempfile
import os
from typing import List, Tuple, Dict, Any

# Import the function to test
from your_module import find_teradata_tables, SQLParsingError

@pytest.fixture
def create_temp_sql_file():
    """Fixture to create a temporary SQL file for testing."""
    temp_dir = tempfile.mkdtemp()
    temp_file = Path(temp_dir) / "test_teradata.sql"
    
    def _create_file(content: str) -> Path:
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return temp_file
    
    yield _create_file
    
    # Cleanup
    if temp_file.exists():
        os.unlink(temp_file)
    os.rmdir(temp_dir)

# Define test cases for parametrization
test_cases = [
    # Basic cases
    {
        "id": "basic_select",
        "sql": "SELECT * FROM SourceTable;",
        "expected_source": ["SourceTable"],
        "expected_temp": []
    },
    {
        "id": "basic_create",
        "sql": "CREATE TABLE TempTable (id INT);",
        "expected_source": [],
        "expected_temp": ["TempTable"]
    },
    
    # Quoted identifiers
    {
        "id": "quoted_identifiers",
        "sql": 'SELECT * FROM "Schema"."Table With Spaces";',
        "expected_source": ["Schema.Table With Spaces"],
        "expected_temp": []
    },
    {
        "id": "escaped_quotes",
        "sql": 'SELECT * FROM "Table with ""quotes"" in name";',
        "expected_source": ['Table with "quotes" in name'],
        "expected_temp": []
    },
    
    # CREATE TABLE variants
    {
        "id": "create_table_variants",
        "sql": """
        CREATE TABLE RegularTable (id INT);
        CREATE SET TABLE SetTable (id INT);
        CREATE MULTISET TABLE MultisetTable (id INT);
        CREATE VOLATILE TABLE VolatileTable (id INT);
        CREATE GLOBAL TEMPORARY TABLE GlobalTempTable (id INT);
        """,
        "expected_source": [],
        "expected_temp": ["RegularTable", "SetTable", "MultisetTable", "VolatileTable", "GlobalTempTable"]
    },
    
    # Common Table Expressions (CTEs)
    {
        "id": "single_cte",
        "sql": """
        WITH SimpleCTE AS (
            SELECT * FROM SourceTable
        )
        SELECT * FROM SimpleCTE;
        """,
        "expected_source": ["SourceTable"],
        "expected_temp": ["SimpleCTE"]
    },
    {
        "id": "multiple_ctes",
        "sql": """
        WITH 
            CTE1 AS (SELECT * FROM Table1),
            CTE2 AS (SELECT * FROM Table2)
        SELECT * FROM CTE1 JOIN CTE2 ON CTE1.id = CTE2.id;
        """,
        "expected_source": ["Table1", "Table2"],
        "expected_temp": ["CTE1", "CTE2"]
    },
    {
        "id": "recursive_cte",
        "sql": """
        WITH RECURSIVE RecursiveCTE AS (
            SELECT * FROM BaseTable
            UNION ALL
            SELECT * FROM RecursiveCTE WHERE id > 0
        )
        SELECT * FROM RecursiveCTE;
        """,
        "expected_source": ["BaseTable"],
        "expected_temp": ["RecursiveCTE"]
    },
    
    # CASE expressions
    {
        "id": "simple_case",
        "sql": """
        SELECT 
            CASE 
                WHEN value > 100 THEN 'High'
                WHEN value BETWEEN 50 AND 100 THEN 'Medium'
                ELSE 'Low' 
            END AS category
        FROM SourceTable;
        """,
        "expected_source": ["SourceTable"],
        "expected_temp": []
    },
    {
        "id": "nested_case",
        "sql": """
        SELECT 
            CASE 
                WHEN value > 100 THEN 
                    CASE 
                        WHEN region = 'North' THEN 'North High'
                        ELSE 'Other High' 
                    END
                ELSE 'Low' 
            END AS category
        FROM SourceTable;
        """,
        "expected_source": ["SourceTable"],
        "expected_temp": []  # Should not include 'North' or 'Other' as tables
    },
    
    # Comma-separated tables
    {
        "id": "comma_separated",
        "sql": """
        SELECT * FROM Table1, Table2, "Schema3"."Table3";
        """,
        "expected_source": ["Table1", "Table2", "Schema3.Table3"],
        "expected_temp": []
    },
    
    # JOIN clauses
    {
        "id": "join_variants",
        "sql": """
        SELECT * FROM Table1 
        INNER JOIN Table2 ON Table1.id = Table2.id
        LEFT JOIN Table3 ON Table1.id = Table3.id
        RIGHT JOIN "Schema4"."Table4" ON Table1.id = "Schema4"."Table4".id
        FULL OUTER JOIN Table5 ON Table1.id = Table5.id;
        """,
        "expected_source": ["Table1", "Table2", "Table3", "Schema4.Table4", "Table5"],
        "expected_temp": []
    },
    
    # Subqueries
    {
        "id": "subquery",
        "sql": """
        SELECT * FROM (SELECT * FROM InnerTable) AS SubQuery;
        """,
        "expected_source": ["InnerTable"],
        "expected_temp": []  # SubQuery is an alias, not a table
    },
    
    # MERGE statements
    {
        "id": "merge",
        "sql": """
        MERGE INTO TargetTable AS tgt
        USING SourceTable AS src
        ON tgt.id = src.id
        WHEN MATCHED THEN UPDATE SET tgt.value = src.value
        WHEN NOT MATCHED THEN INSERT (id, value) VALUES (src.id, src.value);
        """,
        "expected_source": ["SourceTable"],
        "expected_temp": ["TargetTable"]
    },
    
    # CREATE VIEW
    {
        "id": "create_view",
        "sql": """
        CREATE VIEW MyView AS
        SELECT * FROM SourceTable;
        """,
        "expected_source": ["SourceTable"],
        "expected_temp": ["MyView"]
    },
    
    # RENAME TABLE
    {
        "id": "rename_table",
        "sql": """
        RENAME TABLE OldTable TO NewTable;
        """,
        "expected_source": ["OldTable"],
        "expected_temp": ["NewTable"]
    },
    
    # Table with schema and database qualifiers
    {
        "id": "qualified_names",
        "sql": """
        SELECT * FROM Database.Schema.Table;
        """,
        "expected_source": ["Database.Schema.Table"],
        "expected_temp": []
    },
    
    # Comments
    {
        "id": "comments",
        "sql": """
        /* Block comment with table reference TableInComment */
        -- Line comment with table reference TableInComment
        SELECT * FROM RealTable; -- Comment after SQL
        """,
        "expected_source": ["RealTable"],
        "expected_temp": []  # Should not include TableInComment
    },
    
    # INSERT statement
    {
        "id": "insert",
        "sql": """
        INSERT INTO TargetTable
        SELECT * FROM SourceTable;
        """,
        "expected_source": ["SourceTable"],
        "expected_temp": ["TargetTable"]
    },
    
    # UPDATE statement
    {
        "id": "update",
        "sql": """
        UPDATE TargetTable
        SET column1 = value1
        WHERE column2 IN (SELECT id FROM SourceTable);
        """,
        "expected_source": ["SourceTable"],
        "expected_temp": ["TargetTable"]
    },
    
    # DELETE statement
    {
        "id": "delete",
        "sql": """
        DELETE FROM TargetTable
        WHERE column IN (SELECT id FROM SourceTable);
        """,
        "expected_source": ["SourceTable"],
        "expected_temp": ["TargetTable"]
    },
    
    # COLLECT STATISTICS
    {
        "id": "collect_statistics",
        "sql": """
        COLLECT STATISTICS ON TableName COLUMN (column1);
        """,
        "expected_source": ["TableName"],
        "expected_temp": []
    },
    
    # LOCKING TABLE
    {
        "id": "locking_table",
        "sql": """
        LOCKING TABLE TableName FOR ACCESS;
        """,
        "expected_source": ["TableName"],
        "expected_temp": []
    },
    
    # Mixed case sensitivity
    {
        "id": "case_sensitivity",
        "sql": """
        SELECT * FROM MixedCaseTable;
        """,
        "expected_source": ["MixedCaseTable"],  # Should preserve case
        "expected_temp": []
    },
    
    # Keywords that might be mistaken for tables
    {
        "id": "keywords",
        "sql": """
        SELECT * FROM RealTable WHERE column = 'FROM' OR column = 'TABLE';
        """,
        "expected_source": ["RealTable"],
        "expected_temp": []  # Should not include FROM or TABLE as tables
    },
    
    # Edge cases with whitespace
    {
        "id": "whitespace",
        "sql": """
        SELECT    *    FROM    
           RealTable   
        WHERE    column = 'value';
        """,
        "expected_source": ["RealTable"],
        "expected_temp": []
    },
    
    # Common SQL patterns
    {
        "id": "common_patterns",
        "sql": """
        SELECT t1.col1, t2.col2
        FROM Table1 t1
        JOIN Table2 t2 ON t1.id = t2.id
        WHERE t1.status = 'Active'
        GROUP BY t1.col1, t2.col2
        HAVING COUNT(*) > 0
        ORDER BY t1.col1 DESC;
        """,
        "expected_source": ["Table1", "Table2"],
        "expected_temp": []
    },
    
    # Complex multi-statement SQL
    {
        "id": "complex_multi_statement",
        "sql": """
        /* Complex SQL with multiple statements and patterns */
        -- Initialize variables
        
        -- Create tables for analysis
        CREATE VOLATILE TABLE TempSales AS (
            SELECT item_id, sale_date FROM "MyDatabase"."FactSales_Archive"
        ) WITH DATA ON COMMIT PRESERVE ROWS;
        
        -- Create views for reporting
        CREATE VIEW "UserView" AS
        SELECT * FROM DimProduct DP JOIN TempSales TS ON DP.item_id = TS.item_id;
        
        -- Insert data from analysis
        INSERT INTO FinalReport_Table
        SELECT dv.col1, ts.col2 FROM UserView dv JOIN TempSales ts ON dv.id = ts.id;
        
        -- Update configuration
        UPDATE "Schema1"."Configuration" SET value = 'processed' WHERE id = 10;
        
        -- Clean up old logs
        DELETE FROM LogTable_Old;
        
        -- Merge inventory data
        MERGE INTO "TargetDB"."FactInventory" TGT
        USING StagingInventory_Main SRC
        ON TGT.product_key = SRC.product_key
        WHEN MATCHED THEN UPDATE SET quantity = SRC.new_quantity
        WHEN NOT MATCHED THEN INSERT (product_key, quantity) VALUES (SRC.product_key, SRC.new_quantity);
        
        -- Lock tables for processing
        LOCKING TABLE "MyDatabase"."FactSales_Archive" FOR ACCESS;
        
        -- Collect statistics for query optimization
        COLLECT STATISTICS ON FinalReport_Table COLUMN (product_id);
        
        -- Rename tables
        RENAME TABLE OldFeatureTable TO NewFeatureTable;
        
        -- Complex CTE with multiple CTEs
        WITH 
            ProductData AS (
                SELECT product_id, product_name, category 
                FROM DimProduct 
                WHERE active_flag = 'Y'
            ),
            RegionalSales AS (
                SELECT 
                    product_id, 
                    region,
                    SUM(quantity) AS total_quantity
                FROM FactSales
                GROUP BY product_id, region
            )
        SELECT 
            pd.product_name,
            pd.category,
            rs.region,
            rs.total_quantity,
            CASE 
                WHEN rs.total_quantity > 1000 THEN 'High Volume'
                WHEN rs.total_quantity BETWEEN 500 AND 1000 THEN 'Medium Volume'
                ELSE 'Low Volume' 
            END AS volume_category
        FROM ProductData pd
        JOIN RegionalSales rs ON pd.product_id = rs.product_id
        ORDER BY rs.total_quantity DESC;
        """,
        "expected_source": [
            "DimProduct", 
            "FactSales",
            "LogTable_Old",
            "MyDatabase.FactSales_Archive", 
            "OldFeatureTable",
            "StagingInventory_Main", 
            "UserView"
        ],
        "expected_temp": [
            "FinalReport_Table",
            "NewFeatureTable",
            "ProductData",
            "RegionalSales",
            "Schema1.Configuration",
            "TargetDB.FactInventory", 
            "TempSales"
        ]
    }
]

@pytest.mark.parametrize("test_case", test_cases, ids=[tc["id"] for tc in test_cases])
def test_find_teradata_tables(create_temp_sql_file, test_case):
    """Parametrized test for find_teradata_tables function."""
    sql = test_case["sql"]
    expected_source = sorted(test_case["expected_source"])
    expected_temp = sorted(test_case["expected_temp"])
    
    file_path = create_temp_sql_file(sql)
    source, temp = find_teradata_tables(file_path)
    
    # Sort results for consistent comparison
    source = sorted(source)
    temp = sorted(temp)
    
    # For detailed error messages, check differences
    source_missing = [t for t in expected_source if t not in source]
    source_extra = [t for t in source if t not in expected_source]
    temp_missing = [t for t in expected_temp if t not in temp]
    temp_extra = [t for t in temp if t not in expected_temp]
    
    # Build detailed error message if needed
    error_msg = []
    if source_missing:
        error_msg.append(f"Missing source tables: {source_missing}")
    if source_extra:
        error_msg.append(f"Unexpected source tables: {source_extra}")
    if temp_missing:
        error_msg.append(f"Missing temp tables: {temp_missing}")
    if temp_extra:
        error_msg.append(f"Unexpected temp tables: {temp_extra}")
    
    assert source == expected_source and temp == expected_temp, "\n".join(error_msg)

# Error handling tests

def test_nonexistent_file():
    """Test error handling for nonexistent file."""
    with pytest.raises(FileNotFoundError):
        find_teradata_tables(Path("/nonexistent/path/to/file.sql"))

def test_permission_error(monkeypatch):
    """Test error handling for permission error."""
    # Mock open to raise PermissionError
    def mock_open(*args, **kwargs):
        raise PermissionError("Permission denied")
    
    monkeypatch.setattr("builtins.open", mock_open)
    
    with pytest.raises(PermissionError):
        find_teradata_tables(Path("dummy.sql"))

def test_decode_error(monkeypatch, create_temp_sql_file):
    """Test error handling for decode error."""
    # Create a file with binary content that will cause a decode error
    temp_file = create_temp_sql_file("SELECT * FROM Table1;")
    
    # Mock open to raise UnicodeDecodeError
    original_open = open
    def mock_open(*args, **kwargs):
        if 'encoding' in kwargs:
            raise UnicodeDecodeError('utf-8', b'\x80', 0, 1, 'invalid start byte')
        return original_open(*args, **kwargs)
    
    monkeypatch.setattr("builtins.open", mock_open)
    
    with pytest.raises(UnicodeDecodeError):
        find_teradata_tables(temp_file)

def test_parsing_error(monkeypatch, create_temp_sql_file):
    """Test error handling for parsing error."""
    temp_file = create_temp_sql_file("SELECT * FROM Table1;")
    
    # Mock a function in the parser to raise an exception
    def mock_function(*args, **kwargs):
        raise Exception("Parsing error")
    
    # Patch a critical function in your implementation
    monkeypatch.setattr("re.sub", mock_function)
    
    with pytest.raises(SQLParsingError):
        find_teradata_tables(temp_file)

# Test for edge cases with special characters

@pytest.mark.parametrize("special_case", [
    {
        "id": "unicode_identifiers",
        "sql": 'SELECT * FROM "Table_Üñîçødé";',
        "expected_source": ["Table_Üñîçødé"],
        "expected_temp": []
    },
    {
        "id": "mixed_quotes",
        "sql": "SELECT * FROM \"Table_With_'Mixed'_Quotes\";",
        "expected_source": ["Table_With_'Mixed'_Quotes"],
        "expected_temp": []
    },
    {
        "id": "number_prefixed",
        "sql": "SELECT * FROM Table_123;",
        "expected_source": ["Table_123"],
        "expected_temp": []
    },
    {
        "id": "special_characters",
        "sql": "SELECT * FROM Table_$pecial#Chars;",
        "expected_source": ["Table_$pecial#Chars"],
        "expected_temp": []
    }
], ids=lambda x: x["id"])
def test_special_character_handling(create_temp_sql_file, special_case):
    """Test handling of special characters in table names."""
    sql = special_case["sql"]
    expected_source = sorted(special_case["expected_source"])
    expected_temp = sorted(special_case["expected_temp"])
    
    file_path = create_temp_sql_file(sql)
    source, temp = find_teradata_tables(file_path)
    
    assert sorted(source) == expected_source
    assert sorted(temp) == expected_temp

# Performance test (optional)
def test_performance_large_file(create_temp_sql_file):
    """Test performance with a large SQL file."""
    # Generate a large SQL file with many statements
    large_sql = ""
    for i in range(100):
        large_sql += f"""
        -- Statement group {i}
        SELECT * FROM SourceTable_{i};
        CREATE TABLE TempTable_{i} AS SELECT * FROM SourceTable_{i};
        UPDATE TargetTable_{i} SET col = 'value' WHERE id = {i};
        
        """
    
    file_path = create_temp_sql_file(large_sql)
    
    # Verify it completes in a reasonable time
    import time
    start_time = time.time()
    source, temp = find_teradata_tables(file_path)
    elapsed_time = time.time() - start_time
    
    # Check that expected tables were found
    assert len(source) >= 200  # Should find at least 200 tables
    assert len(temp) >= 200    # Should find at least 200 tables
    
    # Optional performance assertion (adjust threshold as needed)
    assert elapsed_time < 5  # Should complete in less than 5 seconds
    
    print(f"Large file test completed in {elapsed_time:.2f} seconds")
    print(f"Found {len(source)} source tables and {len(temp)} temp tables")

if __name__ == "__main__":
    pytest.main(["-vx", __file__])