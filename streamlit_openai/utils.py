from typing import Callable, Dict, Any

class CustomFunction():
    """
    Represents a custom function that can be invoked by the OpenAI API.

    Attributes:
        name (str): The name of the function.
        description (str): A brief description of what the function does.
        parameters (Dict[str, Any]): The parameters required by the function.
        handler (Callable): The actual function to be executed.
    """
    def __init__(
            self,
            name: str,
            description: str,
            parameters: Dict[str, Any],
            handler: Callable,
    ) -> None:
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler

    def __repr__(self) -> str:
        return f"CustomFunction(name='{self.name}')"