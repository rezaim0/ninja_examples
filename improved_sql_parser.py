import sqlparse
from pathlib import Path

def find_tables_sqlparse(file: Path) -> tuple[list[str], list[str]]:
    # print(f"\nDEBUG: Starting find_tables_sqlparse for file: {file.name}")
    try:
        with open(file, "r", encoding='utf-8') as f:
            sql_content = f.read()
    except FileNotFoundError: raise
    except Exception as e: raise

    source_tables_set = set()
    temp_tables_set = set()
    parsed_statements = sqlparse.parse(sql_content)

    for stmt_idx, stmt in enumerate(parsed_statements):
        # print(f"\nDEBUG: Stmt {stmt_idx+1}, Type: {stmt.get_type()}")
        current_statement_aliases = set() 

        # --- 1. Temporary Tables/Views ---
        if stmt.get_type() == 'CREATE':
            tokens = stmt.tokens; create_keyword_index = -1
            for idx, t in enumerate(tokens):
                if t.is_whitespace or isinstance(t, sqlparse.sql.Comment): continue
                if t.ttype is sqlparse.tokens.DDL and t.value.upper() == 'CREATE': create_keyword_index = idx; break
                else: break 
            if create_keyword_index != -1:
                object_type_keyword_value = None; object_name_token = None
                for i in range(create_keyword_index + 1, len(tokens)):
                    token_c = tokens[i] # Renamed token to token_c
                    if token_c.is_whitespace or isinstance(token_c, sqlparse.sql.Comment): continue
                    if token_c.is_keyword and token_c.value.upper() in ('TABLE', 'VIEW'):
                        object_type_keyword_value = token_c.value.upper()
                        for j in range(i + 1, len(tokens)):
                            name_cand = tokens[j] # Renamed to avoid clash
                            if name_cand.is_whitespace or isinstance(name_cand, sqlparse.sql.Comment): continue
                            if isinstance(name_cand, sqlparse.sql.Identifier): object_name_token = name_cand
                            break 
                        break 
                    elif token_c.is_keyword and token_c.value.upper() in ('VOLATILE','SET','MULTISET','GLOBAL','TEMPORARY','OR','REPLACE'): continue
                    else: break 
                if object_name_token and object_type_keyword_value:
                    full_name = str(object_name_token)
                    if full_name: temp_tables_set.add(full_name)
        
        # --- 2. Source Tables ---
        from_or_join_active = False
        stream_tokens = list(stmt.flatten())
        current_token_idx = 0

        while current_token_idx < len(stream_tokens):
            token = stream_tokens[current_token_idx]
            raw_token_str = str(token).strip()

            if token.is_whitespace or isinstance(token, sqlparse.sql.Comment):
                current_token_idx += 1; continue
            
            # print(f"DEBUG: Token: '{raw_token_str}' (idx: {current_token_idx}, from_active: {from_or_join_active}, aliases: {current_statement_aliases})")

            # Activate on FROM/JOIN
            if token.is_keyword and token.value.upper() in ('FROM', 'JOIN'):
                from_or_join_active = True
                # print(f"DEBUG: Activated by '{token.value.upper()}'")
                current_token_idx += 1; continue # Consume FROM/JOIN, process next token

            if from_or_join_active:
                potential_table_name_found = None
                table_name_ends_at_idx = current_token_idx # Index of the last token of the identified table name

                # Try to identify schema.table
                if isinstance(token, sqlparse.sql.Identifier):
                    identifier_str = str(token)
                    if identifier_str.count('.') == 1:
                        schema_part = identifier_str.split('.')[0]
                        if schema_part not in current_statement_aliases:
                            potential_table_name_found = identifier_str
                elif token.ttype is sqlparse.tokens.Name: # Construct schema.table
                    schema_part = str(token).strip()
                    idx_dot = current_token_idx + 1
                    while idx_dot < len(stream_tokens) and stream_tokens[idx_dot].is_whitespace: idx_dot += 1
                    if idx_dot < len(stream_tokens) and str(stream_tokens[idx_dot]).strip() == '.':
                        idx_table_part = idx_dot + 1
                        while idx_table_part < len(stream_tokens) and stream_tokens[idx_table_part].is_whitespace: idx_table_part += 1
                        if idx_table_part < len(stream_tokens) and stream_tokens[idx_table_part].ttype is sqlparse.tokens.Name:
                            table_part = str(stream_tokens[idx_table_part]).strip()
                            if schema_part not in current_statement_aliases:
                                potential_table_name_found = f"{schema_part}.{table_part}"
                                table_name_ends_at_idx = idx_table_part

                if potential_table_name_found:
                    # Heuristic: if table name like alias.column is followed by ')' it's a function argument
                    is_func_arg = False
                    if '.' in potential_table_name_found:
                        peek_idx = table_name_ends_at_idx + 1
                        while peek_idx < len(stream_tokens) and (stream_tokens[peek_idx].is_whitespace or isinstance(stream_tokens[peek_idx], sqlparse.sql.Comment)): peek_idx += 1
                        if peek_idx < len(stream_tokens) and str(stream_tokens[peek_idx]).strip() == ')':
                            is_func_arg = True
                            # print(f"DEBUG: Rejected '{potential_table_name_found}' as func arg (followed by ')')")

                    if not is_func_arg:
                        source_tables_set.add(potential_table_name_found)
                        # print(f"DEBUG:   ADDED SRC: '{potential_table_name_found}'")
                        current_token_idx = table_name_ends_at_idx # Ensure index is at end of table name

                        # Collect alias for this table
                        alias_search_idx = current_token_idx + 1
                        while alias_search_idx < len(stream_tokens) and stream_tokens[alias_search_idx].is_whitespace: alias_search_idx += 1
                        if alias_search_idx < len(stream_tokens):
                            tok_after_table = stream_tokens[alias_search_idx]
                            has_as = False
                            if tok_after_table.is_keyword and tok_after_table.value.upper() == 'AS':
                                has_as = True; alias_search_idx += 1
                                while alias_search_idx < len(stream_tokens) and stream_tokens[alias_search_idx].is_whitespace: alias_search_idx += 1
                            
                            if alias_search_idx < len(stream_tokens):
                                alias_cand_tok = stream_tokens[alias_search_idx]
                                if (isinstance(alias_cand_tok, sqlparse.sql.Identifier) or alias_cand_tok.ttype is sqlparse.tokens.Name) and '.' not in str(alias_cand_tok):
                                    alias_name = str(alias_cand_tok).strip()
                                    current_statement_aliases.add(alias_name)
                                    current_token_idx = alias_search_idx # Consume alias
                                    # print(f"DEBUG:     Collected alias '{alias_name}'")
                    else: # Was a function argument
                        from_or_join_active = False # Deactivate from this internal FROM path

                    # After table/alias (or func arg rejection), check for comma to stay active for current FROM/JOIN clause part
                    if from_or_join_active : # Check if not deactivated by func arg
                        next_significant_idx = current_token_idx + 1
                        while next_significant_idx < len(stream_tokens) and stream_tokens[next_significant_idx].is_whitespace: next_significant_idx += 1
                        if next_significant_idx < len(stream_tokens) and str(stream_tokens[next_significant_idx]).strip() == ',':
                            current_token_idx = next_significant_idx # Consume comma, stay active
                            # print(f"DEBUG: Comma found. Consumed. Staying active.")
                        else:
                            from_or_join_active = False # Not a comma, so this table sequence ends. Next FROM/JOIN will re-trigger.
                            # print(f"DEBUG: No comma after table/alias. Deactivating.")
                
                else: # Current token (when active) did not form a table. It must be a clause ender or other.
                    if token.is_keyword and token.value.upper() not in ('AS', 'ON', 'USING', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'OUTER', 'CROSS', 'LATERAL'):
                        from_or_join_active = False
                    elif token.match(sqlparse.tokens.Punctuation, '('): from_or_join_active = False
                    elif token.match(sqlparse.tokens.Punctuation, ','): pass # Stray comma, keep active? Or error. For now, pass.
                    elif token.ttype is sqlparse.tokens.Punctuation: from_or_join_active = False
                    elif isinstance(token, sqlparse.sql.Identifier) or token.ttype is sqlparse.tokens.Name : from_or_join_active = False # e.g. an alias by itself
                    # print(f"DEBUG: Token '{raw_token_str}' ended active FROM/JOIN sequence.")
            
            current_token_idx += 1
            
    return list(source_tables_set), list(temp_tables_set)