import sys
import click
from pathlib import Path
from typing import Optional
from loguru import logger
from io import StringIO
from agent import MacatoAgent  # Assuming MacatoAgent is defined in agent.py

# Global log buffer for testing
log_buffer = StringIO()

def setup_logger() -> None:
    """
    Set up the logger with appropriate sinks for both stderr and log buffer.
    
    The log buffer is used for testing purposes, while stderr is used for displaying errors.
    """
    logger.remove()  # Remove any existing handlers
    logger.add(log_buffer, format="{message}")  # Log to buffer for testing
    logger.add(sys.stderr, format="{message}", level="ERROR")  # Log errors to stderr

@click.group()
def cli() -> None:
    """
    Macato CLI for updating various tables.
    
    This CLI provides functionality to update fields, versions, and output tables
    individually or all at once.
    """
    pass

@cli.command()
@click.option('--fields', is_flag=True, help="Update fields table")
@click.option('--versions', is_flag=True, help="Update versions table")
@click.option('--output', is_flag=True, help="Update output table")
@click.option('--model', type=click.Path(exists=True), help="Path to the model .pkl file")
@click.option('--all', 'update_all', is_flag=True, help="Update all tables")
def update_table(fields: bool, versions: bool, output: bool, model: Optional[str], update_all: bool) -> None:
    """
    Update specified tables or all tables based on flags.
    
    Args:
        fields (bool): Flag to update fields table.
        versions (bool): Flag to update versions table.
        output (bool): Flag to update output table.
        model (Optional[str]): Path to the model .pkl file.
        update_all (bool): Flag to update all tables.
    
    Raises:
        click.ClickException: If there's an error during the update process.
    """
    setup_logger()  # Initialize the logger
    agent = MacatoAgent()  # Initialize the agent for updating tables

    try:
        # Check for update_all flag and handle accordingly
        if update_all:
            if not model:
                raise click.ClickException("Error: --model is required when using --all")
            agent.load_model(Path(model))
            logger.success(f"Model loaded successfully from {model}")
            agent.update_fields()
            logger.success("Fields table updated successfully.")
            agent.update_docato_version()
            logger.success("Versions table updated successfully.")
            agent.update_output()
            logger.success("Output table updated successfully.")
        else:
            # Handle individual updates
            if fields:
                agent.update_fields()
                logger.success("Fields table updated successfully.")
            if versions:
                agent.update_docato_version()
                logger.success("Versions table updated successfully.")
            if output:
                if not model:
                    raise click.ClickException("Error: --model is required when updating output")
                agent.load_model(Path(model))
                logger.success(f"Model loaded successfully from {model}")
                agent.update_output()
                logger.success("Output table updated successfully.")
        
        # If no flags provided, raise an error
        if not any([fields, versions, output, update_all]):
            raise click.ClickException("Error: No update options provided.")
    
    except Exception as e:
        logger.error(f"Error updating tables: {e}")
        sys.exit(1)  # Exit with error code on exception

if __name__ == '__main__':
    cli()
import sys
import click
from pathlib import Path
from typing import Optional
from loguru import logger
from io import StringIO
from agent import MacatoAgent  # Assuming MacatoAgent is defined in agent.py

# Global log buffer for testing
log_buffer = StringIO()

def setup_logger() -> None:
    """
    Set up the logger with appropriate sinks for both stderr and log buffer.
    
    The log buffer is used for testing purposes, while stderr is used for displaying errors.
    """
    logger.remove()  # Remove any existing handlers
    logger.add(log_buffer, format="{message}")  # Log to buffer for testing
    logger.add(sys.stderr, format="{message}", level="ERROR")  # Log errors to stderr

@click.group()
def cli() -> None:
    """
    Macato CLI for updating various tables.
    
    This CLI provides functionality to update fields, versions, and output tables
    individually or all at once.
    """
    pass

@cli.command()
@click.option('--fields', is_flag=True, help="Update fields table")
@click.option('--versions', is_flag=True, help="Update versions table")
@click.option('--output', is_flag=True, help="Update output table")
@click.option('--model', type=click.Path(exists=True), help="Path to the model .pkl file")
@click.option('--all', 'update_all', is_flag=True, help="Update all tables")
def update_table(fields: bool, versions: bool, output: bool, model: Optional[str], update_all: bool) -> None:
    """
    Update specified tables or all tables based on flags.
    
    Args:
        fields (bool): Flag to update fields table.
        versions (bool): Flag to update versions table.
        output (bool): Flag to update output table.
        model (Optional[str]): Path to the model .pkl file.
        update_all (bool): Flag to update all tables.
    
    Raises:
        click.ClickException: If there's an error during the update process.
    """
    setup_logger()  # Initialize the logger
    agent = MacatoAgent()  # Initialize the agent for updating tables

    try:
        # Check for update_all flag and handle accordingly
        if update_all:
            if not model:
                raise click.ClickException("Error: --model is required when using --all")
            agent.load_model(Path(model))
            logger.success(f"Model loaded successfully from {model}")
            agent.update_fields()
            logger.success("Fields table updated successfully.")
            agent.update_docato_version()
            logger.success("Versions table updated successfully.")
            agent.update_output()
            logger.success("Output table updated successfully.")
        else:
            # Handle individual updates
            if fields:
                agent.update_fields()
                logger.success("Fields table updated successfully.")
            if versions:
                agent.update_docato_version()
                logger.success("Versions table updated successfully.")
            if output:
                if not model:
                    raise click.ClickException("Error: --model is required when updating output")
                agent.load_model(Path(model))
                logger.success(f"Model loaded successfully from {model}")
                agent.update_output()
                logger.success("Output table updated successfully.")
        
        # If no flags provided, raise an error
        if not any([fields, versions, output, update_all]):
            raise click.ClickException("Error: No update options provided.")
    
    except Exception as e:
        logger.error(f"Error updating tables: {e}")
        sys.exit(1)  # Exit with error code on exception

if __name__ == '__main__':
    cli()
