import sys
import click
from pathlib import Path
from typing import Optional
from loguru import logger
from agent import MacatoAgent  # Assuming MacatoAgent is defined in agent.py

@click.group()
def cli() -> None:
    """
    Macato CLI for updating various tables.
    
    This CLI provides functionality to update fields, versions, and output tables
    individually or all at once. It serves as the main entry point for the Macato
    command-line interface, grouping various commands related to table updates.
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
    agent = MacatoAgent()  # Initialize the agent for updating tables
    model_must_exist_message = "Error: --model is required when using --all"
    
    # Check for update_all flag and handle accordingly
    if update_all:
        if not model:
            raise ValueError(model_must_exist_message)
        agent.load_model(Path(model))
        logger.info(f"Model loaded successfully from {model}")
        agent.update_fields()
        logger.info("Fields table updated successfully.")
        agent.update_docato_version()
        logger.info("Versions table updated successfully.")
        agent.update_output()
        logger.info("Output table updated successfully.")
    else:
        # Handle individual updates
        if fields:
            agent.update_fields()
            logger.info("Fields table updated successfully.")
        if versions:
            agent.update_docato_version()
            logger.info("Versions table updated successfully.")
        if output:
            if not model:
                logger.error(model_must_exist_message)
                sys.exit(1)
            agent.load_model(Path(model))
            logger.info(f"Model loaded successfully from {model}")
            agent.update_output()
            logger.info("Output table updated successfully.")
    
    # If no flags provided, raise an error
    if not any([fields, versions, output, update_all]):
        logger.error("No update options provided.")
        logger.error("No update option specified. Please use --fields, --versions, --output, or --all.")

if __name__ == '__main__':
    cli()
###############################################################

import sys
import click
from pathlib import Path
from typing import Optional
from loguru import logger

@cli.command('update-table')
@click.option('--fields', is_flag=True, help="Update fields table")
@click.option('--versions', is_flag=True, help="Update versions table")
@click.option('--output', is_flag=True, help="Update output table")
@click.option('--model', type=click.Path(exists=True), help="Path to the model .pkl file")
def update_table(fields: bool, versions: bool, output: bool, model: Optional[str]) -> None:
    """
    Update specified tables based on flags.
    """
    agent = MacatoAgent()
    
    # Check if all options are selected
    all_selected = fields and versions and output
    
    # Validate model path when necessary
    if (output or all_selected) and not model:
        logger.error("--model is required when updating the output table or all tables")
        sys.exit(1)
    
    # Load model if needed
    if output or all_selected:
        try:
            agent.load_model(Path(model))
            logger.info(f"Model loaded successfully from {model}")
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            sys.exit(1)
    
    # Perform updates
    try:
        if fields or all_selected:
            agent.update_fields()
            logger.info("Fields table updated successfully.")
        
        if versions or all_selected:
            agent.update_docato_version()
            logger.info("Versions table updated successfully.")
        
        if output or all_selected:
            agent.update_output()
            logger.info("Output table updated successfully.")
    except Exception as e:
        logger.error(f"An error occurred during table update: {str(e)}")
        sys.exit(1)
    
    # If no flags provided, show help
    if not any([fields, versions, output]):
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        ctx.exit()