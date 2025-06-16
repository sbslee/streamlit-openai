from typing import Callable, Dict, Any, List

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
    
class RemoteMCP():
    """
    Represents a remote MCP server that can be used to perform tasks.

    Attributes:
        server_label (str): A label for the server.
        server_url (str): The URL of the remote MCP server.
        require_approval (str): Indicates whether approval is required for actions (default: "never").
        headers (Dict[str, Any]): Optional headers to include in requests to the server.
        allowed_tools (List[str]): A list of tools that are allowed to be used with this server.
    """
    def __init__(
        self,
        server_label,
        server_url,
        require_approval: str = "never",
        headers: Dict[str, Any] = None,
        allowed_tools: List[str] = None,
    ) -> None:
        self.server_label = server_label
        self.server_url = server_url
        self.require_approval = require_approval
        self.headers = headers
        self.allowed_tools = allowed_tools

    def __repr__(self) -> str:
        return f"RemoteMCP(server_label='{self.server_label}')"