from pathlib import Path
from typing import List, Tuple
import re

def find_tables(file: Path) -> Tuple[List[str], List[str]]:
    """
    Extracts source and temporary tables from a Teradata SQL file.
    Aims for simplicity and 90-95% accuracy.

    Args:
        file (Path): The path to the SQL file.

    Returns:
        Tuple[List[str], List[str]]: A tuple containing two lists:
            - source_table: Tables referenced in FROM, JOIN, INTO, USING clauses.
            - temp_table: Tables created or referenced in TABLE or VIEW clauses.
    """
    try:
        # Read and normalize the file content
        with open(file, "r", encoding="utf-8") as f: # Specify encoding
            text_file = f.read().lower()
    except FileNotFoundError:
        print(f"Error: File not found at {file}")
        return [], []
    except Exception as e:
        print(f"Error reading file {file}: {e}")
        return [], []

    # Remove block comments (/* ... */)
    text_file = re.sub(r"/\*.*?\*/", "", text_file, flags=re.DOTALL)

    # Remove single-line comments (--)
    lines = text_file.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped_line = line.strip()
        if not stripped_line.startswith("--"):
            cleaned_lines.append(line) # Keep original spacing for statement context
    text_file = "\n".join(cleaned_lines)

    # Split into SQL statements (basic split, acknowledges limitations for complex scripts)
    statements = [stmt.strip() for stmt in text_file.split(";") if stmt.strip()]

    # Define keywords
    # k_words: keywords indicating a source table follows
    k_words = ["from", "join", "into", "using"] 
    # i_words: keywords indicating a table/view definition or reference (often for creation/alteration)
    i_words = ["table", "view"] 
    # All SQL keywords to avoid misidentifying them as table names
    sql_keywords_to_avoid = set(k_words + i_words + [
        "select", "insert", "update", "delete", "create", "alter", "drop", "truncate",
        "where", "group", "order", "by", "on", "as", "distinct", "all", "and", "or", "not",
        "set", "values", "database", "volatile", "multiset", "procedure", "case", "when",
        "then", "else", "end", "begin", "with", "recursive", "exists", "in", "like", "is",
        "null", "between", "union", "except", "intersect", "cast", "grant", "revoke"
        # Add more common SQL keywords if needed
    ])


    source_table = []
    temp_table = []

    for stmt in statements:
        # Replace multiple spaces/newlines within a statement with a single space for easier splitting
        normalized_stmt = re.sub(r'\s+', ' ', stmt)
        words = normalized_stmt.split()

        for index, keyword_candidate in enumerate(words):
            # Check if the current word is one of our target keywords
            current_word_is_k_word = keyword_candidate in k_words
            current_word_is_i_word = keyword_candidate in i_words

            if not (current_word_is_k_word or current_word_is_i_word):
                continue # Not a keyword we are interested in

            # Ensure there's a next word
            if index >= len(words) - 1:
                continue
            
            next_word_raw = words[index + 1]
            # Basic cleanup of the potential table name
            # Allow '.' for schema.table, '-' and '_' for table names.
            # Strip common delimiters but be careful not to remove parts of valid names.
            # Regex to find the first valid part of a potential table name
            match = re.match(r'^([a-z0-9_.-]+)', next_word_raw)
            if not match:
                continue
            
            next_word = match.group(1).strip(",:;()")


            # Heuristics for a valid-looking table name
            if (
                next_word  # Not an empty string
                and not next_word.isdigit()  # Not purely a number
                and "/" not in next_word  # Not a file path
                and "\\" not in next_word # Not a file path
                and not next_word.startswith("<")  # Not a placeholder like <parameter>
                and not next_word.startswith("(") # Not starting with a parenthesis (e.g. subquery alias)
                and not next_word.endswith(")")   # Not ending with a parenthesis
                and not next_word.endswith(".")   # Not ending with a stray dot
                and next_word not in sql_keywords_to_avoid # Not an SQL keyword
                and any(c.isalnum() for c in next_word) # Contains at least one alphanumeric char
                and len(next_word) > 1 # Avoid very short, ambiguous names (e.g. single letters unless intended)
            ):
                # Categorize based on the keyword
                if current_word_is_k_word:
                    source_table.append(next_word)
                elif current_word_is_i_word:
                    # For "TABLE" or "VIEW", check if it's part of a CREATE/REPLACE statement
                    # This makes "temp_table" more about definitions.
                    # For simplicity, as per original docstring "referenced in TABLE or VIEW clauses"
                    # this check can be optional. If we want strictly "created" tables,
                    # we'd look at words[index-1] for "create" or "replace".
                    # Given the "referenced in" part, any table after "TABLE" or "VIEW" is added.
                    temp_table.append(next_word)
            
    # Remove duplicates and return
    return list(set(source_table)), list(set(temp_table))

if __name__ == '__main__':
    # Create a dummy SQL file for testing
    test_sql_content = """
    /* This is a block comment */
    CREATE VOLATILE TABLE temp_user_data AS (
        SELECT 
            user_id,
            user_name,
            email_address -- single line comment
        FROM staging.raw_users src
        WHERE active_flag = 1
    ) WITH DATA PRIMARY INDEX (user_id);

    -- Another comment
    INSERT INTO db_prod.final_user_summary (user_id, name, email)
    SELECT 
        tud.user_id, 
        tud.user_name,
        tud.email_address
    FROM temp_user_data tud;

    CREATE VIEW reporting.active_users_view AS
    SELECT id FROM db_prod.final_user_summary WHERE status = 'active';

    MERGE INTO target_table tgt
    USING (SELECT id, data FROM source_changes) AS src
    ON tgt.id = src.id
    WHEN MATCHED THEN UPDATE SET data = src.data
    WHEN NOT MATCHED THEN INSERT (id, data) VALUES (src.id, src.data);

    SELECT * FROM another_source_table;
    SELECT field FROM "yet-another-table"; -- Quoted table name
    """
    dummy_file = Path("test_script.sql")
    with open(dummy_file, "w", encoding="utf-8") as f:
        f.write(test_sql_content)

    s_tables, t_tables = find_tables(dummy_file)

    print("Source Tables Found:")
    for table in sorted(s_tables):
        print(f"- {table}")

    print("\nTemporary/Defined Tables Found:")
    for table in sorted(t_tables):
        print(f"- {table}")
    
    # Clean up dummy file
    dummy_file.unlink()

    # Test with a non-existent file
    print("\nTesting with non-existent file:")
    find_tables(Path("non_existent_file.sql"))
