import os

import dotenv

# Load envirnment variables from .env file upon module start.
dotenv.load_dotenv(verbose=True)


_MISSING = object()


def getenv(variable: str, default=_MISSING) -> str:
    """
    Get the value of the specified environment variable.

    Args:
        variable (str): The name of the environment variable to retrieve.
        default: Value to return if the variable is not defined.

    Returns:
        str: The value of the specified environment variable.

    Raises:
        NameError: If the specified environment variable is not defined and no
            default is given.
    """
    value = os.getenv(variable)
    if value is not None:
        return value
    if default is not _MISSING:
        return default
    raise NameError(f"Error: {variable} Environment Variable not Defined")


def getenv_bool(variable: str, default: bool = False) -> bool:
    """
    Get the specified environment variable as a boolean.

    Args:
        variable (str): The name of the environment variable to retrieve.
        default (bool): Value to return if the variable is not defined.

    Returns:
        bool: The parsed value.

    Raises:
        ValueError: If the variable is set to an unrecognized value, rather
            than silently falling back to the default.
    """
    value = os.getenv(variable)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in ("1", "true", "yes", "on"):
        return True
    if normalized in ("0", "false", "no", "off", ""):
        return False
    raise ValueError(f"{variable} must be a boolean value, got {value!r}")
