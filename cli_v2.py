import click
from pathlib import Path
from typing import Optional
from agent import MacatoAgent  # Assuming MacatoAgent is defined in agent.py
from loguru import logger

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
    Update specified tables or all tables.

    This function updates the specified tables based on the provided flags.
    If --all is specified, it updates all tables.

    Args:
        fields (bool): Flag to update fields table.
        versions (bool): Flag to update versions table.
        output (bool): Flag to update output table.
        model (Optional[str]): Path to the model .pkl file.
        update_all (bool): Flag to update all tables.

    Raises:
        click.ClickException: If there's an error during the update process.

    Returns:
        None
    """
    agent = MacatoAgent()

    if update_all:
        if not model:
            raise click.ClickException("Error: --model is required when using --all")
        try:
            agent.load_model(Path(model))
            logger.success(f"Model loaded successfully from {model}")
            agent.update_fields()
            logger.success("Fields table updated successfully.")
            agent.update_docato_version()
            logger.success("Versions table updated successfully.")
            agent.update_output()
            logger.success("Output table updated successfully.")
            logger.success("All tables updated successfully.")
        except Exception as e:
            raise click.ClickException(f"Error updating all tables: {str(e)}")
        return

    try:
        if output or update_all:
            if not model:
                raise click.ClickException("Error: --model is required when updating output")
            agent.load_model(Path(model))
            logger.success(f"Model loaded successfully from {model}")

        if fields:
            agent.update_fields()
            logger.success("Fields table updated successfully.")

        if versions:
            agent.update_docato_version()
            logger.success("Versions table updated successfully.")

        if output:
            agent.update_output()
            logger.success("Output table updated successfully.")

    except Exception as e:
        raise click.ClickException(f"Error updating tables: {str(e)}")

if __name__ == '__main__':
    cli()