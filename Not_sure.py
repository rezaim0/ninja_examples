
def extract_tables(sql_file: Optional[List[Path]] = None, flib_modules: Optional[List[str]] = None) -> None:
    """
    Extracts source tables from provided SQL files or specified modules.
    """
    # Initialize parameters if None to avoid mutable default arguments
    if sql_file is None:
        sql_file = []
    if flib_modules is None:
        flib_modules = []

    # Configure the logger to capture all levels
    logger.remove()
    logger.add(sys.stderr, level="DEBUG", format="{level}: {message}")

    # Check that at least one of sql_file or flib_modules is provided
    if not sql_file and not flib_modules:
        logger.error("No SQL files or modules have been provided.")
        sys.exit(1)

    # Process flib_modules if provided
    if flib_modules:
        # Remove duplicates (case-insensitive)
        seen_modules = set()
        unique_flib_modules = []
        for mod in flib_modules:
            mod_normalized = mod.strip().lower()
            logger.debug(f"Checking module: '{mod}' (normalized: '{mod_normalized}')")
            if mod_normalized and mod_normalized not in seen_modules:
                seen_modules.add(mod_normalized)
                unique_flib_modules.append(mod)
                logger.debug(f"Added new module: '{mod}'")
            elif mod_normalized:
                logger.warning(f"Duplicate module detected and ignored: {mod}")
            else:
                logger.warning(f"Empty module name detected and ignored.")

        flib_modules = unique_flib_modules

        # Log if no valid modules remain after deduplication and cleaning
        if not flib_modules:
            logger.error("No valid modules have been provided after processing.")
            sys.exit(1)

        logger.info(f"Fetching SQL files for modules: {flib_modules}")
        try:
            sql_file_paths = get_sql_file_paths(flib_modules)

            # Log modules that were not found
            found_modules = list(sql_file_paths.keys())
            missing_modules = [mod for mod in flib_modules if mod.lower() not in [m.lower() for m in found_modules]]
            if missing_modules:
                logger.warning(f"Modules not found: {missing_modules}")

            if not sql_file_paths:
                logger.error("No SQL files found for the specified modules.")
                sys.exit(1)

            # Convert paths to Path objects and extend sql_file list
            module_sql_files = [Path(path) for path in sql_file_paths.values()]
            sql_file.extend(module_sql_files)
        except Exception as e:
            logger.error(f"An error occurred while fetching SQL files: {e}")
            sys.exit(1)

    # Check that the sql files have been provided (after processing modules)
    if not sql_file:
        logger.error("No SQL files have been provided.")
        sys.exit(1)

    # Generate list of source tables
    try:
        logger.debug(f"Extracting source tables from SQL files: {sql_file}")
        table_list = extract_source_tables(sql_file)
    except Exception as e:
        logger.error(f"An error occurred while extracting source tables: {e}")
        sys.exit(1)

    if table_list:
        logger.info("Source tables have been found.")
    else:
        logger.warning(f"No source tables were found in {sql_file}")
        sys.exit(1)

    # Print in DOC-friendly format
    for source_table in table_list:
        print(f"    - {source_table}")
