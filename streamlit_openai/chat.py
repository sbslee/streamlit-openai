import streamlit as st
import openai
import os, json, re, tempfile, zipfile, time
from pathlib import Path
from typing import Optional, List, Union, Literal, Dict, Any
from .utils import CustomFunction
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

MIME_TYPES = {
    "txt" : "text/plain",
    "csv" : "text/csv",
    "tsv" : "text/tab-separated-values",
    "html": "text/html",
    "yaml": "text/yaml",
    "md"  : "text/markdown",
    "png" : "image/png",
    "jpg" : "image/jpeg",
    "jpeg": "image/jpeg",
    "gif" : "image/gif",
    "xml" : "application/xml",
    "json": "application/json",
    "pdf" : "application/pdf",
    "zip" : "application/zip",
    "tar" : "application/x-tar",
    "gz"  : "application/gzip",
}

class Chat():
    """A Streamlit-based chat interface powered by OpenAI's Responses API."""
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
        allow_file_search: Optional[bool] = True,
    ) -> None:
        """
        Initializes a Chat instance.

        Args:
            api_key (str): API key for OpenAI. If not provided, fetched from environment variable `OPENAI_API_KEY`.
            model (str): The OpenAI model to use (default: "gpt-4o").
            instructions (str): Instructions for the assistant.
            temperature (float): Sampling temperature for the model (default: 1.0).
            accept_file (bool or str): Whether the chat input should accept files (True, False, or "multiple") (default: "multiple").
            uploaded_files (list): List of files to be uploaded to the assistant during initialization.
            functions (list): List of custom functions to be attached to the assistant.
            user_avatar (str): An emoji, image URL, or file path that represents the user.
            assistant_avatar (str): An emoji, image URL, or file path that represents the assistant.
            placeholder (str): Placeholder text for the chat input box (default: "Your message").
            welcome_message (str): Welcome message from the assistant.
            example_messages (list): List of example messages for the user to choose from.
            info_message (str): Information message to be displayed in the chat.
            vector_store_ids (list): List of vector store IDs for file search. Only used if file search is enabled.
            history (str): File path to the chat history ZIP file. If provided, the chat history will be loaded from this file.
            allow_code_interpreter (bool): Whether to allow code interpreter functionality (default: True).
            allow_file_search (bool): Whether to allow file search functionality (default: True).
        """
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
        self.allow_file_search = allow_file_search
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
        self._dynamic_vector_store = None

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

        # File search currently allows a maximum of two vector stores
        if allow_file_search and self.vector_store_ids is not None:
            self._tools.append({
                "type": "file_search",
                "vector_store_ids": self.vector_store_ids
            })

        # If a welcome message is provided, add it to the chat history
        if self.welcome_message is not None:
            self._input.append({"role": "assistant", "content": self.welcome_message})
            self.add_section(
                "assistant",
                blocks=[self.create_block("text", self.welcome_message)]
            )

        # If files are uploaded statically, create tracked files for them
        if self.uploaded_files is not None:
            for uploaded_file in self.uploaded_files:
                self.track(uploaded_file)

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
                        self.add_section(
                            section["role"],
                            blocks=[self.create_block(block["category"], block["content"]) for block in section["blocks"]]
                        )
                        for block in section["blocks"]:
                            self._input.append({
                                "role": section["role"],
                                "content": block["content"]
                            })

    @property
    def last_section(self) -> Optional["Section"]:
        """Returns the last section of the chat."""
        return self._sections[-1] if self._sections else None

    def respond(self, prompt) -> None:
        """Sends the user prompt to the assistant and streams the response."""
        self._input.append({"role": "user", "content": prompt})
        self.add_section("assistant")
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
                if event1.annotation["type"] == "file_citation":
                    pass
                elif event1.annotation["type"] == "container_file_citation":                
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
        """Runs the main assistant loop."""
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
            self.add_section(
                "user",
                blocks=[self.create_block("text", prompt)]
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
                    self.add_section(
                        "user",
                        blocks=[self.create_block("text", self._selected_example)]
                    )
                    self.respond(self._selected_example)

    def handle_files(self, uploaded_files) -> None:
        """Handles uploaded files."""
        if uploaded_files is None:
            return
        else:
            for uploaded_file in uploaded_files:
                if uploaded_file.file_id in [x.uploaded_file.file_id for x in self._tracked_files if isinstance(x, UploadedFile)]:
                    continue
                self.track(uploaded_file)

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
        """A file that is tracked by the chat."""
        def __init__(
            self,
            chat: "Chat",
            uploaded_file: Optional[Union[UploadedFile, str]]
        ) -> None:
            """
            Initializes a TrackedFile instance.
            
            Args:
                chat (Chat): The parent Chat object.
                uploaded_file (UploadedFile or str): An UploadedFile object or a string representing the file path.
            """
            self.chat = chat
            self.uploaded_file = uploaded_file
            self._file_path = None
            self._openai_file = None
            self._vision_file = None
            self._skip_file_search = False

            if isinstance(self.uploaded_file, str):
                self._file_path = Path(self.uploaded_file).resolve()
            elif isinstance(self.uploaded_file, UploadedFile):
                self._file_path = Path(os.path.join(self.chat._temp_dir.name, self.uploaded_file.name))
                with open(self._file_path, "wb") as f:
                    f.write(self.uploaded_file.getvalue())
            else:
                raise ValueError("uploaded_file must be an instance of UploadedFile or a string representing the file path.")

            self.chat._input.append(
                {"role": "user", "content": [{"type": "input_text", "text": f"File locally available at: {self._file_path}"}]}
            )

            if self._file_path.suffix == ".pdf":
                if self._openai_file is None:
                    with open(self._file_path, "rb") as f:
                        self._openai_file = self.chat._client.files.create(file=f, purpose="user_data")
                try:
                    # Test if the PDF file can be processed
                    response = self.chat._client.responses.create(
                        model=self.chat.model,
                        input=[{
                            "role": "user",
                            "content": [{"type": "input_file", "file_id": self._openai_file.id
                        }]}]
                    )
                    self.chat._input.append({
                        "role": "user",
                        "content": [{"type": "input_file", "file_id": self._openai_file.id}]
                    })
                    self._skip_file_search = True
                except Exception as e:
                    pass

            if self.chat.allow_code_interpreter and self._file_path.suffix in CODE_INTERPRETER_EXTENSIONS:
                if self._openai_file is None:
                    with open(self._file_path, "rb") as f:
                        self._openai_file = self.chat._client.files.create(file=f, purpose="user_data")
                self.chat._client.containers.files.create(
                    container_id=self.chat._container_id,
                    file_id=self._openai_file.id,
                )

            if self.chat.allow_file_search and not self._skip_file_search and self._file_path.suffix in FILE_SEARCH_EXTENSIONS:
                if self._openai_file is None:
                    with open(self._file_path, "rb") as f:
                        self._openai_file = self.chat._client.files.create(file=f, purpose="user_data")
                if self.chat._dynamic_vector_store is None:
                    self.chat._dynamic_vector_store = self.chat._client.vector_stores.create(
                        name="streamlit-openai"
                    )
                self.chat._client.vector_stores.files.create(
                    vector_store_id=self.chat._dynamic_vector_store.id,
                    file_id=self._openai_file.id
                )
                result = self.chat._client.vector_stores.retrieve(
                    vector_store_id=self.chat._dynamic_vector_store.id,
                )
                while result.status != "completed":
                    time.sleep(1)
                    result = self.chat._client.vector_stores.retrieve(
                        vector_store_id=self.chat._dynamic_vector_store.id,
                    )
                for tool in self.chat._tools:
                    if tool["type"] == "file_search":
                        if self.chat._dynamic_vector_store.id not in tool["vector_store_ids"]:
                            tool["vector_store_ids"].append(self.chat._dynamic_vector_store.id)
                        break
                else:
                    self.chat._tools.append({
                        "type": "file_search",
                        "vector_store_ids": [self.chat._dynamic_vector_store.id]
                    })

            if self._file_path.suffix in VISION_EXTENSIONS:
                self._vision_file = self.chat._client.files.create(file=self._file_path, purpose="vision")
                self.chat._input.append({
                    "role": "user",
                    "content": [{"type": "input_image", "file_id": self._vision_file.id}]
                })

        def __repr__(self) -> None:
            return f"TrackedFile(uploaded_file='{self._file_path.name}')"
        
    def track(self, uploaded_file) -> None:
        """Tracks a file uploaded by the user."""
        self._tracked_files.append(
            self.TrackedFile(self, uploaded_file)
        )

    class Block():
        """A block of content in the chat."""
        def __init__(
                self,
                chat: "Chat",
                category: str,
                content: Optional[Union[str, bytes, openai.File]] = None,
        ) -> None:
            """
            Initializes a Block instance.
            
            Args:
                chat (Chat): The parent Chat object.
                category (str): The type of content ('text', 'code', 'image', or 'download').
                content (str, bytes, or openai.File): The actual content of the block. This can be a string for text or code, bytes for images, or an `openai.File` object for downloadable files.
            """
            self.chat = chat
            self.category = category
            self.content = content

            if self.content is None:
                self.content = ""
            else:
                self.content = content

        def __repr__(self) -> None:
            if self.category in ["text", "code"]:
                content = self.content
                if len(content) > 30:
                    content = content[:30].strip() + "..."
                content = repr(content)
            elif self.category == "image":
                content = "Bytes"
            elif self.category == "download":
                content = f"File(filename='{os.path.basename(self.content.filename)}')"
            return f"Block(category='{self.category}', content={content})"

        def iscategory(self, category) -> bool:
            """Checks if the block belongs to the specified category."""
            return self.category == category

        def write(self) -> None:
            """Renders the block's content to the chat."""
            if self.category == "text":
                st.markdown(self.content)
            elif self.category == "code":
                st.code(self.content)
            elif self.category == "image":
                st.image(self.content)
            elif self.category == "download":
                cfile_content = self.chat._client.containers.files.content.retrieve(
                    file_id=self.content,
                    container_id=self.chat._container_id
                )
                cfile = self.chat._client.containers.files.retrieve(
                    file_id=self.content,
                    container_id=self.chat._container_id                
                )
                filename = os.path.basename(cfile.path)
                _, file_extension = os.path.splitext(filename)
                st.download_button(
                    label=filename,
                    data=cfile_content.read(),
                    file_name=filename,
                    mime=MIME_TYPES[file_extension.lstrip(".")],
                    icon=":material/download:",
                    key=self.chat._download_button_key,
                )
                self.chat._download_button_key += 1

        def to_dict(self) -> Dict[str, Any]:
            """Converts the block to a dictionary representation."""
            if self.category in ["text", "code"]:
                content = self.content
            elif self.category == "image":
                content = "Bytes"
            elif self.category == "download":
                content = f"File(filename='{os.path.basename(self.content.filename)}')"
            return {
                "category": self.category,
                "content": content,
            }

    def create_block(self, category, content=None) -> "Block":
        """Creates a new block object."""
        return self.Block(self, category, content=content)

    class Section():
        """A section of the chat."""
        def __init__(
                self,
                chat: "Chat",
                role: str,
                blocks: Optional[List["Block"]] = None,
        ) -> None:
            """
            Initializes a Section instance.
            
            Attributes:
                chat (Chat): The parent Chat object.
                role (str): The role associated with this message (e.g., "user" or "assistant").
                blocks (list): A list of Block instances representing message segments.
            """
            self.chat = chat
            self.role = role
            self.blocks = blocks
            self.delta_generator = st.empty()
            
        def __repr__(self) -> None:
            return f"Section(role='{self.role}', blocks={self.blocks})"

        @property
        def empty(self) -> bool:
            """Returns True if the section has no blocks."""
            return self.blocks is None

        @property
        def last_block(self) -> Optional["Block"]:
            """Returns the last block in the section or None if empty."""
            return None if self.empty else self.blocks[-1]

        def update(self, category, content) -> None:
            """Updates the section with new content, appending or extending existing blocks."""
            if self.empty:
                self.blocks = [self.chat.create_block(category, content)]
            elif category in ["text", "code"] and self.last_block.iscategory(category):
                self.last_block.content += content
            else:
                self.blocks.append(self.chat.create_block(category, content))

        def write(self) -> None:
            """Renders the section's content in the Streamlit chat interface."""
            if self.empty:
                pass
            else:
                with st.chat_message(self.role, avatar=self.chat.user_avatar if self.role == "user" else self.chat.assistant_avatar):
                    for block in self.blocks:
                        block.write()

        def update_and_stream(self, category, content) -> None:
            """Updates the section and streams the update live to the UI."""
            self.update(category, content)
            self.stream()

        def stream(self) -> None:
            """Renders the section content using Streamlit's delta generator."""
            with self.delta_generator:
                self.write()

        def to_dict(self) -> Dict[str, Any]:
            """Converts the section to a dictionary representation."""
            if self.empty:
                return {}
            else:
                return {
                    "role": self.role,
                    "blocks": [block.to_dict() for block in self.blocks],
                }

    def add_section(self, role, blocks=None) -> None:
        """Adds a new Section."""
        self._sections.append(
            self.Section(self, role, blocks=blocks)
        )