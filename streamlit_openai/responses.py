import streamlit as st
import openai
import os, json, tempfile
from pathlib import Path
from typing import Optional, List, Union, Literal
from .utils import Container, Block, CustomFunction
from streamlit.runtime.uploaded_file_manager import UploadedFile

DEVELOPER_MESSAGE = """
- Use GitHub-flavored Markdown in your response, including tables, images, URLs, code blocks, and lists.
- Wrap all mathematical expressions and LaTeX terms in `$...$` for inline math and `$$...$$` for display math.
"""

FILE_SEARCH_EXTENSIONS = [
    ".c", ".cpp", ".cs", ".css", ".doc", ".docx", ".go", 
    ".html", ".java", ".js", ".json", ".md", ".pdf", ".php", 
    ".pptx", ".py", ".rb", ".sh", ".tex", ".ts", ".txt"
]

class Responses():
    """
    A chat interface using OpenAI's Responses API.

    This class manages a message history and streams assistant responses in a 
    chat-like interface.

    Attributes:
        api_key (str): API key for OpenAI. If not provided, fetched from environment variable `OPENAI_API_KEY`.
        model (str): The OpenAI model used for chat completions (default: "gpt-4o").
        accept_file (bool or str): Whether the chat input should accept files (True, False, or "multiple") (default: "multiple").
        functions (list): Optional list of custom function tools to be attached to the assistant.
        user_avatar (str): An emoji, image URL, or file path that represents the user.
        assistant_avatar (str): An emoji, image URL, or file path that represents the assistant.
        instructions (str): Instructions for the assistant.
        temperature (float): Sampling temperature for the model (default: 1.0).
        placeholder (str): Placeholder text for the chat input box (default: "Your message").
        welcome_message (str): Welcome message from the assistant.
        message_files (list): List of files to be uploaded to the assistant during initialization. Currently, only PDF files are supported.
        example_messages (list): A list of example messages for the user to choose from.
        info_message (str): Information message to be displayed in the chat.
        vector_store_ids (list): List of vector store IDs for file search. Only used if file_search is enabled.
        client (openai.OpenAI): The OpenAI client instance for API calls.
        input (list): The chat history in OpenAI's expected message format.
        containers (list): List to track the conversation history in structured form.
        tools (list): A list of tools derived from function definitions for the assistant to call.
        tracked_files (list): List of files being tracked for uploads/removals.
        selected_example_message (str): The selected example message from the list of example messages.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = "gpt-4o",
        accept_file: Union[bool, Literal["multiple"]] = "multiple",
        functions: Optional[List[CustomFunction]] = None,
        user_avatar: Optional[str] = None,
        assistant_avatar: Optional[str] = None,
        instructions: Optional[str] = None,
        temperature: Optional[float] = 1.0,
        placeholder: Optional[str] = "Your message",
        welcome_message: Optional[str] = None,
        message_files: Optional[List[str]] = None,
        example_messages: Optional[List[dict]] = None,
        info_message: Optional[str] = None,
        vector_store_ids: Optional[List[str]] = None,
    ) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY") if api_key is None else api_key
        self.model = model
        self.accept_file = accept_file
        self.functions = functions
        self.user_avatar = user_avatar
        self.assistant_avatar = assistant_avatar
        self.instructions = "" if instructions is None else instructions
        self.temperature = temperature
        self.placeholder = placeholder
        self.welcome_message = welcome_message
        self.message_files = message_files
        self.example_messages = example_messages
        self.info_message = info_message
        self.vector_store_ids = vector_store_ids
        self.client = openai.OpenAI(api_key=self.api_key)
        self.input = []
        self.containers = []
        self.tools = []
        self.tracked_files = []
        self.temp_dir = tempfile.TemporaryDirectory()
        self.selected_example_message = None

        if self.functions is not None:
            self.tools = []
            for function in self.functions:
                self.tools.append({
                    "type": "function",
                    "name": function.definition["name"],
                    "description": function.definition["description"],
                    "parameters": function.definition["parameters"],
                })

        if self.vector_store_ids is not None:
            self.tools.append({"type": "file_search", "vector_store_ids": self.vector_store_ids})

        # If a welcome message is provided, add it to the chat history
        if self.welcome_message is not None:
            self.input.append({"role": "assistant", "content": self.welcome_message})
            self.containers.append(
                Container(self, "assistant", blocks=[Block(self, "text", self.welcome_message)])
            )

        # If message files are provided, upload them to the assistant
        if self.message_files is not None:
            for message_file in self.message_files:
                tracked_file = TrackedFile(self, message_file=message_file)
                self.tracked_files.append(tracked_file)

    @property
    def last_container(self) -> Optional[Container]:
        return self.containers[-1] if self.containers else None

    def _respond1(self) -> None:
        """Streams a simple assistant response without tool usage."""
        events = self.client.responses.create(
            model=self.model,
            input=self.input,
            instructions=DEVELOPER_MESSAGE+self.instructions,
            temperature=self.temperature,
            tools=self.tools,
            stream=True,
        )
        response = ""
        for event in events:
            if event.type == "response.output_text.delta":
                self.last_container.update_and_stream("text", event.delta)
                response += event.delta
        self.input.append({"role": "assistant", "content": response})

    def _respond2(self) -> None:
        """Streams assistant response with support for tool calls."""
        events1 = self.client.responses.create(
            model=self.model,
            input=self.input,
            instructions=DEVELOPER_MESSAGE+self.instructions,
            temperature=self.temperature,
            tools=self.tools,
            stream=True,
        )
        response1 = ""
        tool_calls = {}
        for event1 in events1:
            if event1.type == "response.output_text.delta":
                self.last_container.update_and_stream("text", event1.delta)
                response1 += event1.delta
            elif event1.type == "response.output_item.done" and event1.item.type == "function_call":
                tool_calls[event1.item.name] = event1
        if response1:
            self.input.append({"role": "assistant", "content": response1})
        if tool_calls:
            for tool in tool_calls:
                function = [x for x in self.functions if x.definition["name"] == tool][0]
                result = function.function(**json.loads(tool_calls[tool].item.arguments))
                self.input.append({
                    "type": "function_call",
                    "id": tool_calls[tool].item.id,
                    "call_id": tool_calls[tool].item.call_id,
                    "name": tool_calls[tool].item.name,
                    "arguments": tool_calls[tool].item.arguments,
                })
                self.input.append({
                    "type": "function_call_output",
                    "call_id": tool_calls[tool].item.call_id,
                    "output": str(result)
                })
            events2 = self.client.responses.create(
                model=self.model,
                input=self.input,
                instructions=DEVELOPER_MESSAGE+self.instructions,
                temperature=self.temperature,
                tools=self.tools,
                stream=True,
            )
            response2 = ""
            for event2 in events2:
                if event2.type == "response.output_text.delta":
                    self.last_container.update_and_stream("text", event2.delta)
                    response2 += event2.delta
            if response2:
                self.input.append({"role": "assistant", "content": response2})

    def respond(self, prompt) -> None:
        """Sends the user prompt to the assistant and streams the response."""
        self.input.append({"role": "user", "content": prompt})
        self.containers.append(Container(self, "assistant"))
        if self.functions is None:
            self._respond1()
        else:
            self._respond2()

    def run(self, uploaded_files=None) -> None:
        """Runs the main assistant loop: handles user messages."""
        if self.info_message is not None:
            st.info(self.info_message)
        for container in self.containers:
            container.write()
        chat_input = st.chat_input(placeholder=self.placeholder, accept_file=self.accept_file)
        if chat_input is not None:
            if self.accept_file in [True, "multiple"]:
                prompt = chat_input.text
                if chat_input.files:
                    if uploaded_files is None:
                        uploaded_files = chat_input.files
                    else:
                        uploaded_files.extend(chat_input.files)
            else:
                prompt = chat_input
            with st.chat_message("user"):
                st.markdown(prompt)
            self.containers.append(
                Container(self, "user", blocks=[Block(self, "text", prompt)])
            )
            self.handle_files(uploaded_files)
            self.respond(prompt)
        else:
            if self.example_messages is not None:
                if self.selected_example_message is None:
                    selected_example_message = st.pills(
                        "Examples",
                        options=self.example_messages,
                        label_visibility="collapsed"
                    )
                    if selected_example_message:
                        self.selected_example_message = selected_example_message
                        st.rerun()
                else:
                    with st.chat_message("user"):
                            st.markdown(self.selected_example_message)
                    self.containers.append(
                        Container(self, "user", blocks=[Block(self, "text", self.selected_example_message)])
                    )
                    self.respond(self.selected_example_message)

    def handle_files(self, uploaded_files) -> None:
        """Handles uploaded files and manages tracked file lifecycle."""
        # Handle file uploads
        if uploaded_files is None:
            return
        else:
            for uploaded_file in uploaded_files:
                if uploaded_file.file_id in [x.uploaded_file.file_id for x in self.tracked_files]:
                    continue
                tracked_file = TrackedFile(self, uploaded_file=uploaded_file)
                self.tracked_files.append(tracked_file)

class TrackedFile():
    """
    A class to represent a file that is tracked and managed within the OpenAI 
    and Streamlit integration.

    Attributes:
        chat (ChatCompletions): The ChatCompletions instance that this file is associated with.
        uploaded_file (UploadedFile): The UploadedFile object created by Streamlit.
        message_file (str): The file path of the message file.
        openai_file (File): The File object created by OpenAI.
        file_path (Path): The path to the file on the local filesystem.
    """
    def __init__(
        self,
        chat: Responses,
        uploaded_file: Optional[UploadedFile] = None,
        message_file: Optional[str] = None,
    ) -> None:
        if (uploaded_file is None) == (message_file is None):
            raise ValueError("Exactly one of 'uploaded_file' or 'message_file' must be provided.")
        self.chat = chat
        self.uploaded_file = uploaded_file
        self.message_file = message_file
        self.openai_file = None
        self.vector_store = None

        if self.uploaded_file is not None:
            self.file_path = Path(os.path.join(self.chat.temp_dir.name, self.uploaded_file.name))
            with open(self.file_path, "wb") as f:
                f.write(self.uploaded_file.getvalue())
        else:
            self.file_path = Path(self.message_file).resolve()

        self.chat.input.append(
            {"role": "user", "content": [{"type": "input_text", "text": f"File locally available at: {self.file_path}"}]}
        )

        if self.file_path.suffix in FILE_SEARCH_EXTENSIONS:
            with open(self.file_path, "rb") as f:
                self.openai_file = self.chat.client.files.create(file=f, purpose="assistants")
            self.vector_store = self.chat.client.vector_stores.create()
            self.chat.client.vector_stores.files.create(
                vector_store_id=self.vector_store.id,
                file_id=self.openai_file.id
            )
            result = self.chat.client.vector_stores.files.retrieve(
                vector_store_id=self.vector_store.id,
                file_id=self.openai_file.id,
            )
            while result.status != "completed":
                result = self.chat.client.vector_stores.files.retrieve(
                    vector_store_id=self.vector_store.id,
                    file_id=self.openai_file.id,
                )
            if not self.chat.tools:
                self.chat.tools.append({"type": "file_search", "vector_store_ids": [self.vector_store.id]})
            else:
                for tool in self.chat.tools:
                    if tool["type"] == "file_search":
                        if self.vector_store.id not in tool["vector_store_ids"]:
                            tool["vector_store_ids"].append(self.vector_store.id)
                        break
                else:
                    self.chat.tools.append({"type": "file_search", "vector_store_ids": [self.vector_store.id]})

    def __repr__(self) -> None:
        return f"TrackedFile(uploaded_file='{self.file_path.name}')"