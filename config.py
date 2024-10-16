import os
import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Final, List, Optional

import yaml
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger(__name__)

class Environment(Enum):
    LOCAL = "local"
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"

@dataclass
class DBConfig:
    environment: Environment
    database: str = ""
    schema: Optional[str] = None
    table_names: List[str] = field(default_factory=list)

def load_config(config_path: str = "macato/config.yaml") -> Dict:
    with open(config_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)

def get_user_id_tdm() -> str:
    """
    Retrieves the current user's username and extracts the user ID
    by splitting at '@' and taking the first part.

    Returns:
        str: The user ID (username before '@') or the full username if '@' is not present.

    Raises:
        Exception: If an unexpected error occurs.
    """
    try:
        user_id = os.getuid()
        user_info = pwd.getpwuid(user_id)
        username = user_info.pw_name

        # Split the username at '@' if present
        if '@' in username:
            user_id = username.split('@')[0]
            logger.debug(f"Extracted user ID: {user_id}")
            return user_id
        else:
            logger.debug(f"Username does not contain '@'. Using full username as user ID: {username}")
            return username

    except KeyError:
        logger.error("User ID not found in the password database.")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return None

def get_db_config() -> DBConfig:
    env_str = os.getenv("AEP_ENV", "local").lower()

    try:
        env = Environment(env_str)
    except ValueError:
        raise ValueError(f"Invalid environment specified in AEP_ENV: {env_str}")

    config = load_config()
    env_config = config[env.value]

    table_names = env_config["table_names"]

    if env == Environment.DEV:
        userid = get_user_id_tdm()
        if not userid:
            raise ValueError("USERID could not be extracted from logs for dev environment.")
        table_names = [f"{userid}_{name}" for name in table_names]

    return DBConfig(
        environment=env,
        database=env_config["database"],
        schema=env_config["schema"],
        table_names=table_names,
    )

DATABASE_CONFIG: Final[DBConfig] = get_db_config()
