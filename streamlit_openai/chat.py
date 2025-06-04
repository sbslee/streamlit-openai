import streamlit as st
import openai
import os, json, re, tempfile, zipfile
from pathlib import Path
from typing import Optional, List, Union, Literal
from .utils import Section, Block, CustomFunction
from streamlit.runtime.uploaded_file_manager import UploadedFile

DEVELOPER_MESSAGE = """
- Use GitHub-flavored Markdown in your response, including tables, images, URLs, code blocks, and lists.
- Wrap all mathematical expressions and LaTeX terms in `$...$` for inline math and `$$...$$` for display math.
- When a custom function is called with a file path as its input, you must use the local file path.
"""

CODE_INTERPRETER_EXTENSIONS = [
    ".c", ".cs", ".cpp", ".csv", ".doc", ".docx", ".html", 
    ".java", ".json", ".md", ".pdf", ".php", ".pptx", ".py", 
    ".rb", ".tex", ".txt", ".css", ".js", ".sh", ".ts", ".csv", 
    ".jpeg", ".jpg", ".gif", ".pkl", ".png", ".tar", ".xlsx", 
    ".xml", ".zip"
]

FILE_SEARCH_EXTENSIONS = [
    ".c", ".cpp", ".cs", ".css", ".doc", ".docx", ".go", 
    ".html", ".java", ".js", ".json", ".md", ".pdf", ".php", 
    ".pptx", ".py", ".rb", ".sh", ".tex", ".ts", ".txt"
]

VISION_EXTENSIONS = [".png", ".jpeg", ".jpg", ".webp", ".gif"]

class Chat():
    """
    A chat interface using OpenAI's Responses API.

    This class manages a message history and streams assistant responses in a 
    chat-like interface.

    Attributes:
        api_key (str): API key for OpenAI. If not provided, fetched from environment variable `OPENAI_API_KEY`.
        model (str): The OpenAI model used for chat completions (default: "gpt-4o").
        instructions (str): Instructions for the assistant.
        temperature (float): Sampling temperature for the model (default: 1.0).        
        accept_file (bool or str): Whether the chat input should accept files (True, False, or "multiple") (default: "multiple").
        uploaded_files (list): List of files to be uploaded to the assistant during initialization. Currently, only PDF files are supported.
        functions (list): Optional list of custom function tools to be attached to the assistant.
        user_avatar (str): An emoji, image URL, or file path that represents the user.
        assistant_avatar (str): An emoji, image URL, or file path that represents the assistant.
        placeholder (str): Placeholder text for the chat input box (default: "Your message").
        welcome_message (str): Welcome message from the assistant.
        example_messages (list): A list of example messages for the user to choose from.
        info_message (str): Information message to be displayed in the chat.
        vector_store_ids (list): List of vector store IDs for file search. Only used if file_search is enabled.
        history (str): File path to the chat history ZIP file. If provided, the chat history will be loaded from this file.
        allow_code_interpreter (bool): Whether to allow code interpreter functionality (default: True).
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = "gpt-4o",
        instructions: Optional[str] = None,
        temperature: Optional[float] = 1.0,
        accept_file: Union[bool, Literal["multiple"]] = "multiple",
        uploaded_files: Optional[List[str]] = None,
        functions: Optional[List[CustomFunction]] = None,
        user_avatar: Optional[str] = None,
        assistant_avatar: Optional[str] = None,
        placeholder: Optional[str] = "Your message",
        welcome_message: Optional[str] = None,
        example_messages: Optional[List[dict]] = None,
        info_message: Optional[str] = None,
        vector_store_ids: Optional[List[str]] = None,
        history: Optional[str] = None,
        allow_code_interpreter: Optional[bool] = True,
    ) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY") if api_key is None else api_key
        self.model = model
        self.instructions = "" if instructions is None else instructions
        self.temperature = temperature
        self.accept_file = accept_file
        self.uploaded_files = uploaded_files
        self.functions = functions
        self.user_avatar = user_avatar
        self.assistant_avatar = assistant_avatar
        self.placeholder = placeholder
        self.welcome_message = welcome_message
        self.example_messages = example_messages
        self.info_message = info_message
        self.vector_store_ids = vector_store_ids
        self.history = history
        self.allow_code_interpreter = allow_code_interpreter
        self._client = openai.OpenAI(api_key=self.api_key)
        self._temp_dir = tempfile.TemporaryDirectory()
        self._selected_example = None
        self._input = []
        self._tools = []
        self._previous_response_id = None
        self._container_id = None
        self._sections = []
        self._tracked_files = []
        self._download_button_key = 0

        if self.allow_code_interpreter:
            container = self._client.containers.create(name="container")
            self._container_id = container.id
            self._tools.append({"type": "code_interpreter", "container": self._container_id})

        if self.functions is not None:
            for function in self.functions:
                self._tools.append({
                    "type": "function",
                    "name": function.name,
                    "description": function.description,
                    "parameters": function.parameters,
                })

        if self.vector_store_ids is not None:
            self._tools.append({"type": "file_search", "vector_store_ids": self.vector_store_ids})

        # If a welcome message is provided, add it to the chat history
        if self.welcome_message is not None:
            self._input.append({"role": "assistant", "content": self.welcome_message})
            self._sections.append(
                Section(self, "assistant", blocks=[Block(self, "text", self.welcome_message)])
            )

        # If message files are provided, upload them to the assistant
        if self.uploaded_files is not None:
            for uploaded_file in self.uploaded_files:
                tracked_file = TrackedFile(self, uploaded_file)
                self._tracked_files.append(tracked_file)

        # If a chat history file is provided, load the chat history
        if self.history is not None:
            if not self.history.endswith(".zip"):
                raise ValueError("History file must end with .zip")
            with tempfile.TemporaryDirectory() as t:
                with zipfile.ZipFile(self.history, "r") as f:
                    f.extractall(t)
                with open(f"{t}/{self.history.replace('.zip', '')}/data.json", "r") as f:
                    data = json.load(f)
                    for section in data["sections"]:
                        self._sections.append(Section(
                            self,
                            section["role"],
                            blocks=[Block(self, block["category"], block["content"]) for block in section["blocks"]]
                        ))
                        for block in section["blocks"]:
                            self._input.append({
                                "role": section["role"],
                                "content": block["content"]
                            })

    @property
    def last_section(self) -> Optional[Section]:
        return self._sections[-1] if self._sections else None

    def respond(self, prompt) -> None:
        """Sends the user prompt to the assistant and streams the response."""
        self._input.append({"role": "user", "content": prompt})
        self._sections.append(Section(self, "assistant"))
        events1 = self._client.responses.create(
            model=self.model,
            input=self._input,
            instructions=DEVELOPER_MESSAGE+self.instructions,
            temperature=self.temperature,
            tools=self._tools,
            previous_response_id=self._previous_response_id,
            stream=True,
        )
        self._input = []
        tool_calls = {}
        for event1 in events1:
            if event1.type == "response.completed":
                self._previous_response_id = event1.response.id
            elif event1.type == "response.output_text.delta":
                self.last_section.update_and_stream("text", event1.delta)
                self.last_section.last_block.content = re.sub(r"!?\[([^\]]+)\]\(sandbox:/mnt/data/([^\)]+)\)", r"\1 (`\2`)", self.last_section.last_block.content)
            elif event1.type == "response.code_interpreter_call_code.delta":
                self.last_section.update_and_stream("code", event1.delta)
            elif event1.type == "response.output_item.done" and event1.item.type == "function_call":   
                tool_calls[event1.item.name] = event1
            elif event1.type == "response.output_text.annotation.added":
                if event1.annotation["file_id"] in event1.annotation["filename"]:
                    if Path(event1.annotation["filename"]).suffix in [".png", ".jpg", ".jpeg"]:
                        image_content = self._client.containers.files.content.retrieve(
                            file_id=event1.annotation["file_id"],
                            container_id=self._container_id
                        )
                        self.last_section.update_and_stream("image", image_content.read())
                else:
                    self.last_section.update_and_stream("download", event1.annotation["file_id"])
        if tool_calls:
            for tool in tool_calls:
                function = [x for x in self.functions if x.name == tool][0]
                result = function.handler(**json.loads(tool_calls[tool].item.arguments))
                self._input.append({
                    "type": "function_call_output",
                    "call_id": tool_calls[tool].item.call_id,
                    "output": str(result)
                })
            events2 = self._client.responses.create(
                model=self.model,
                input=self._input,
                instructions=DEVELOPER_MESSAGE+self.instructions,
                temperature=self.temperature,
                tools=self._tools,
                previous_response_id=self._previous_response_id,
                stream=True,
            )
            self._input = []
            for event2 in events2:
                if event2.type == "response.completed":
                    self._previous_response_id = event2.response.id
                elif event2.type == "response.output_text.delta":
                    self.last_section.update_and_stream("text", event2.delta)

    def run(self, uploaded_files=None) -> None:
        """Runs the main assistant loop: handles user messages."""
        if self.info_message is not None:
            st.info(self.info_message)
        for section in self._sections:
            section.write()
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
            self._sections.append(
                Section(self, "user", blocks=[Block(self, "text", prompt)])
            )
            self.handle_files(uploaded_files)
            self.respond(prompt)
        else:
            if self.example_messages is not None:
                if self._selected_example is None:
                    selected_example = st.pills(
                        "Examples",
                        options=self.example_messages,
                        label_visibility="collapsed"
                    )
                    if selected_example:
                        self._selected_example = selected_example
                        st.rerun()
                else:
                    with st.chat_message("user"):
                            st.markdown(self._selected_example)
                    self._sections.append(
                        Section(self, "user", blocks=[Block(self, "text", self._selected_example)])
                    )
                    self.respond(self._selected_example)

    def handle_files(self, uploaded_files) -> None:
        """Handles uploaded files and manages tracked file lifecycle."""
        # Handle file uploads
        if uploaded_files is None:
            return
        else:
            for uploaded_file in uploaded_files:
                if uploaded_file.file_id in [x.uploaded_file.file_id for x in self._tracked_files]:
                    continue
                tracked_file = TrackedFile(self, uploaded_file=uploaded_file)
                self._tracked_files.append(tracked_file)

    def save(self, file_path: str) -> None:
        """Saves the chat history to a ZIP file."""
        if not file_path.endswith(".zip"):
            raise ValueError("File path must end with .zip")
        data = {
            "Sections": [section.to_dict() for section in self._sections],
        }
        with tempfile.TemporaryDirectory() as t:
            with open(f"{t}/data.json", "w") as f:
                json.dump(data, f, indent=4)
            with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as f:
                for root, dirs, files in os.walk(t):
                    for file in files:
                        f.write(
                            os.path.join(root, file),
                            arcname=os.path.join(os.path.basename(file_path.replace(".zip", "")), file)
                        )

class TrackedFile():
    """
    A class to represent a file that is tracked and managed within the OpenAI 
    and Streamlit integration.

    Attributes:
        chat (ChatCompletions): The ChatCompletions instance that this file is associated with.
        uploaded_file (UploadedFile or str): An UploadedFile object or a string representing the file path.
        data (dict): A dictionary to store additional data related to the file.
        file_path (Path): The path to the file on the local filesystem.
    """
    def __init__(
        self,
        chat: Chat,
        uploaded_file: Optional[UploadedFile]
    ) -> None:
        self.chat = chat
        self.uploaded_file = uploaded_file
        self.data = {}
        self.file_path = None

        if isinstance(self.uploaded_file, str):
            self.file_path = Path(self.uploaded_file).resolve()
        elif isinstance(self.uploaded_file, UploadedFile):
            self.file_path = Path(os.path.join(self.chat._temp_dir.name, self.uploaded_file.name))
            with open(self.file_path, "wb") as f:
                f.write(self.uploaded_file.getvalue())
        else:
            raise ValueError("uploaded_file must be an instance of UploadedFile or a string representing the file path.")


        self.chat._input.append(
            {"role": "user", "content": [{"type": "input_text", "text": f"File locally available at: {self.file_path}"}]}
        )

        if self.file_path.suffix in CODE_INTERPRETER_EXTENSIONS:
            with open(self.file_path, "rb") as f:
                openai_file = self.chat._client.files.create(file=f, purpose="assistants")
            self.chat._client.containers.files.create(
                container_id=self.chat._container_id,
                file_id=openai_file.id,
            )
            self.data["code_interpreter"] = {"file_id": openai_file.id}

        if self.file_path.suffix in FILE_SEARCH_EXTENSIONS:
            with open(self.file_path, "rb") as f:
                openai_file = self.chat._client.files.create(file=f, purpose="user_data")
            vector_store = self.chat._client.vector_stores.create()
            self.chat._client.vector_stores.files.create(
                vector_store_id=vector_store.id,
                file_id=openai_file.id
            )
            result = self.chat._client.vector_stores.files.retrieve(
                vector_store_id=vector_store.id,
                file_id=openai_file.id,
            )
            while result.status != "completed":
                result = self.chat._client.vector_stores.files.retrieve(
                    vector_store_id=vector_store.id,
                    file_id=openai_file.id,
                )
            if not self.chat._tools:
                self.chat._tools.append({"type": "file_search", "vector_store_ids": [vector_store.id]})
            else:
                for tool in self.chat._tools:
                    if tool["type"] == "file_search":
                        if self.vector_store.id not in tool["vector_store_ids"]:
                            tool["vector_store_ids"].append(self.vector_store.id)
                        break
                else:
                    self.chat._tools.append({"type": "file_search", "vector_store_ids": [vector_store.id]})
            self.data["file_search"] = {"file_id": openai_file.id, "vector_store_id": vector_store.id}

        if self.file_path.suffix in VISION_EXTENSIONS:
            openai_file = self.chat._client.files.create(file=self.file_path, purpose="vision")
            self.chat._input.append({
                "role": "user",
                "content": [{"type": "input_image", "file_id": openai_file.id}]
            })
            self.data["vision"] = {"file_id": openai_file.id}

    def __repr__(self) -> None:
        return f"TrackedFile(uploaded_file='{self.file_path.name}')"