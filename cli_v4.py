import sys
import click
from pathlib import Path
from typing import Optional
from loguru import logger
from agent import MacatoAgent  # Assuming MacatoAgent is defined in agent.py

# Configure loguru logger
logger.remove()
logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")
logger.add("file_{time}.log", rotation="1 week", level="DEBUG")

class MacatoCliError(click.ClickException):
    """Custom exception for Macato CLI errors that integrates with Click."""
    def __init__(self, message):
        super().__init__(message)
        logger.error(message)

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
    """
    agent = MacatoAgent()  # Initialize the agent for updating tables

    try:
        if update_all:
            if not model:
                raise MacatoCliError("--model is required when using --all")
            agent.load_model(Path(model))
            logger.info(f"Model loaded successfully from {model}")
            agent.update_fields()
            logger.info("Fields table updated successfully.")
            agent.update_docato_version()
            logger.info("Versions table updated successfully.")
            agent.update_output()
            logger.info("Output table updated successfully.")
            logger.success("All tables updated successfully.")
        else:
            if fields:
                agent.update_fields()
                logger.info("Fields table updated successfully.")
            if versions:
                agent.update_docato_version()
                logger.info("Versions table updated successfully.")
            if output:
                if not model:
                    raise MacatoCliError("--model is required when updating output")
                agent.load_model(Path(model))
                logger.info(f"Model loaded successfully from {model}")
                agent.update_output()
                logger.info("Output table updated successfully.")
        
        if not any([fields, versions, output, update_all]):
            logger.warning("No update options provided.")
            click.echo("No update option specified. Please use --fields, --versions, --output, or --all.")
    
    except Exception as e:
        logger.exception(f"Error updating tables: {e}")
        raise MacatoCliError(str(e))

if __name__ == '__main__':
    cli()