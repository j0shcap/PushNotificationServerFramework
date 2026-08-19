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
