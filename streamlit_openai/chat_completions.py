import streamlit as st
import openai
import os, json
from typing import Optional, List
from .utils import Container, Block, CustomFunction

DEVELOPER_MESSAGE = """
- Use GitHub-flavored Markdown in your response, including tables, code blocks, and lists.
- Wrap all mathematical expressions and LaTeX terms in `$...$` for inline math and `$$...$$` for display math.
"""

class ChatCompletions():
    """
    A chat interface using OpenAI's Chat Completions API with optional 
    function calling support.

    This class manages a message history and streams assistant responses using 
    either simple completions or function-enabled completions depending on the 
    provided configuration. It integrates with Streamlit for interactive chat 
    UIs.

    Attributes:
        api_key (str): API key for OpenAI. If not provided, fetched from environment variable `OPENAI_API_KEY`.
        model (str): The OpenAI model used for chat completions (default: "gpt-4o").
        functions (list): Optional list of custom function tools to be attached to the assistant.
        user_avatar (str): An emoji, image URL, or file path that represents the user.
        assistant_avatar (str): An emoji, image URL, or file path that represents the assistant.
        instructions (str): Instructions for the assistant.
        temperature (float): Sampling temperature for the model (default: 1.0).
        placeholder (str): Placeholder text for the chat input box (default: "Your message").
        welcome_message (str): Welcome message from the assistant.
        client (openai.OpenAI): The OpenAI client instance for API calls.
        messages (list): The chat history in OpenAI's expected message format.
        containers (list): List to track the conversation history in structured form.
        tools (list): A list of tools derived from function definitions for the assistant to call.
    """
    def __init__(
            self,
            api_key: Optional[str] = None,
            model: Optional[str] = "gpt-4o",
            functions: Optional[List[CustomFunction]] = None,
            user_avatar: Optional[str] = None,
            assistant_avatar: Optional[str] = None,
            instructions: Optional[str] = None,
            temperature: Optional[float] = 1.0,
            placeholder: Optional[str] = "Your message",
            welcome_message: Optional[str] = None,
    ) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY") if api_key is None else api_key
        self.model = model
        self.functions = functions
        self.user_avatar = user_avatar
        self.assistant_avatar = assistant_avatar
        self.instructions = "" if instructions is None else instructions
        self.temperature = temperature
        self.placeholder = placeholder
        self.welcome_message = welcome_message
        self.client = openai.OpenAI(api_key=self.api_key)
        self.messages = [{"role": "developer", "content": DEVELOPER_MESSAGE+self.instructions}]
        self.containers = []
        
        if self.functions is not None:
            self.tools = []
        if self.functions is not None:
            for function in self.functions:
                self.tools.append({"type": "function", "function": function.definition})

        # If a welcome message is provided, add it to the chat history
        if self.welcome_message is not None:
            self.messages.append({"role": "assistant", "content": self.welcome_message})
            self.containers.append(
                Container("assistant", blocks=[Block("text", self.welcome_message)])
            )

    @property
    def last_container(self) -> Optional[Container]:
        """Returns the last container or None if empty."""
        return self.containers[-1] if self.containers else None

    def _respond1(self) -> None:
        """Streams a simple assistant response without tool usage."""
        chunks = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            stream=True,
            temperature=self.temperature,
        )
        self.messages.append({"role": "assistant", "content": chunks})
        for x in chunks:
            if x.choices[0].delta.content is not None:
                self.last_container.update_and_stream("text", x.choices[0].delta.content)

    def _respond2(self) -> None:
        """Streams assistant response with support for tool calls."""
        chunks = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            stream=True,
            temperature=self.temperature,
            tools=self.tools,
        )
        self.messages.append({"role": "assistant", "content": chunks})
        current_tool = {}
        used_tools = {}
        for x in chunks:
            if x.choices[0].delta.content is not None:
                self.last_container.update_and_stream("text", x.choices[0].delta.content)
            if x.choices[0].finish_reason == "tool_calls":
                used_tools[current_tool["name"]] = current_tool
                current_tool = {}
            if x.choices[0].delta.tool_calls is not None:
                if x.choices[0].delta.tool_calls[0].function.name is not None:
                    if not current_tool or current_tool["name"] != x.choices[0].delta.tool_calls[0].function.name:
                        current_tool = {
                            "name": x.choices[0].delta.tool_calls[0].function.name,
                            "id": x.choices[0].delta.tool_calls[0].id,
                            "args": "",
                        }
                current_tool["args"] += x.choices[0].delta.tool_calls[0].function.arguments
        if used_tools:
            for tool in used_tools:
                self.messages.append({
                    "role": "assistant",
                    "tool_calls": [{
                        "id": used_tools[tool]["id"],
                        "type": "function",
                        "function": {
                            "name": used_tools[tool]["name"],
                            "arguments": used_tools[tool]["args"],
                        }
                    }]
                })

                function = [x for x in self.functions if x.definition["name"] == tool][0]
                result = function.function(**json.loads(used_tools[tool]["args"]))
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": used_tools[tool]["id"],
                    "content": result,
                })

            chunks = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                stream=True,
                temperature=self.temperature,
            )
            self.messages.append({"role": "assistant", "content": chunks})

            for x in chunks:
                if x.choices[0].delta.content is not None:
                    self.last_container.update_and_stream("text", x.choices[0].delta.content)
        
    def respond(self, prompt) -> None:
        """Sends the user prompt to the assistant and streams the response."""
        self.messages.append({"role": "user", "content": prompt})
        self.containers.append(Container("assistant"))
        if self.functions is None:
            self._respond1()
        else:
            self._respond2()
        
    def run(self) -> None:
        """Runs the main assistant loop: handles user messages."""
        for container in self.containers:
            container.write()
        if prompt := st.chat_input(placeholder=self.placeholder):
            with st.chat_message("user"):
                st.markdown(prompt)
            self.containers.append(
                Container("user", blocks=[Block("text", prompt)])
            )
            self.respond(prompt)