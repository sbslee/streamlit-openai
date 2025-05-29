import streamlit as st
import openai
import os, json, re, tempfile, zipfile
from pathlib import Path
from typing import Optional, List
from .utils import Container, Block, CustomFunction
from openai.types.beta import AssistantStreamEvent
from openai.types.beta.threads import Text, TextDelta, ImageFile
from openai.types.beta.threads.runs import ToolCall, ToolCallDelta
from streamlit.runtime.uploaded_file_manager import UploadedFile

DEVELOPER_MESSAGE = """
- Use GitHub-flavored Markdown in your response, including tables, images, URLs, code blocks, and lists.
- Wrap all mathematical expressions and LaTeX terms in `$...$` for inline math and `$$...$$` for display math.
- All hyperlinks to `sandbox:/mnt/data/*` files must be placed at the end of the message. When you output multiple sandbox hyperlinks, do not use bullets, numbers, or any kind of list formatting. Instead, separate each hyperlink with a blank line, like in a paragraph break.
- When a custom function is called with a file path as its input, you must use the local file path.
"""

FILE_SEARCH_EXTENSIONS = [
    ".c", ".cpp", ".cs", ".css", ".doc", ".docx", ".go", 
    ".html", ".java", ".js", ".json", ".md", ".pdf", ".php", 
    ".pptx", ".py", ".rb", ".sh", ".tex", ".ts", ".txt"
]

CODE_INTERPRETER_EXTENSIONS = [
    ".c", ".cs", ".cpp", ".csv", ".doc", ".docx", ".html", 
    ".java", ".json", ".md", ".pdf", ".php", ".pptx", ".py", 
    ".rb", ".tex", ".txt", ".css", ".js", ".sh", ".ts", ".csv", 
    ".jpeg", ".jpg", ".gif", ".pkl", ".png", ".tar", ".xlsx", 
    ".xml", ".zip"
]

VISION_EXTENSIONS = [".png", ".jpeg", ".jpg", ".webp", ".gif"]

class Assistants():
    """
    A class to interact with OpenAI's Assistant API, providing conversational 
    AI functionality with optional support for file search, code execution, 
    and custom functions.

    This class creates or retrieves an assistant, initializes a thread for 
    conversation, and handles user interaction, file uploads, and streaming 
    responses.

    Attributes:
        api_key (str): API key for OpenAI. If not provided, fetched from environment variable `OPENAI_API_KEY`.
        model (str): The model name to be used (default is "gpt-4o").
        name (str): Optional name for the assistant (only used when creating a new assistant).
        assistant_id (str): ID of an existing assistant to retrieve. If not provided, a new one is created.
        functions (list): Optional list of custom function tools to be attached to the assistant.
        file_search (bool): Whether file search capability should be enabled.
        code_interpreter (bool): Whether code interpreter tool should be enabled.
        user_avatar (str): An emoji, image URL, or file path that represents the user.
        assistant_avatar (str): An emoji, image URL, or file path that represents the assistant.
        instructions (str): Instructions for the assistant.
        temperature (float): Sampling temperature for the model (default: 1.0).
        placeholder (str): Placeholder text for the chat input box (default: "Your message").
        welcome_message (str): Welcome message from the assistant.
        message_files (list): List of files to be uploaded to the assistant during initialization.
        example_messages (list): A list of example messages for the user to choose from.
        info_message (str): Information message to be displayed in the chat.
        vector_store_ids (list): List of vector store IDs for file search. Only used if file_search is enabled.
        history (str): File path to the chat history ZIP file. If provided, the chat history will be loaded from this file.
        containers (list): List to track the conversation history in structured form.
        tools (list): Tools (custom functions, file search, code interpreter) enabled for the assistant.
        tracked_files (list): List of files being tracked for uploads/removals.
        assistant (Assistant): The instantiated or retrieved OpenAI assistant.
        thread (Thread): The conversation thread associated with the assistant.
        selected_example_message (str): The selected example message from the list of example messages.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = "gpt-4o",
        name: Optional[str] = None,
        assistant_id: Optional[str] = None,
        functions: Optional[List[CustomFunction]] = None,
        file_search: bool = False,
        code_interpreter: bool = False,
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
        history: Optional[str] = None,
    ) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY") if api_key is None else api_key
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = model
        self.containers = []
        self.functions = functions
        self.tools = None
        self.tracked_files = []
        self.file_search = file_search
        self.code_interpreter = code_interpreter
        self.user_avatar = user_avatar
        self.instructions = "" if instructions is None else instructions
        self.temperature = temperature
        self.placeholder = placeholder
        self.welcome_message = welcome_message
        self.message_files = message_files
        self.example_messages = example_messages
        self.info_message = info_message
        self.vector_store_ids = vector_store_ids
        self.history = history
        self.assistant_avatar = assistant_avatar
        self.assistant_id = assistant_id
        self.assistant = None
        self.thread = None
        self.download_button_key = 0
        self.temp_dir = tempfile.TemporaryDirectory()
        self.selected_example_message = None

        if self.file_search or self.code_interpreter or self.functions is not None:
            self.tools = []
        if self.file_search:
            self.tools.append({"type": "file_search"})
        if self.code_interpreter:
            self.tools.append({"type": "code_interpreter"})
        if self.functions is not None:
            for function in self.functions:
                self.tools.append({"type": "function", "function": function.definition})

        tool_resources = {}
        if self.file_search and self.vector_store_ids is not None:
            tool_resources["file_search"] = {"vector_store_ids": self.vector_store_ids}

        # Create or retrieve the assistant
        if self.assistant_id is None:
            self.assistant = self.client.beta.assistants.create(
                name=name,
                instructions=DEVELOPER_MESSAGE+self.instructions,
                model=self.model,
                tools=self.tools,
                temperature=self.temperature,
                tool_resources=tool_resources,
            )
        else:
            self.assistant = self.client.beta.assistants.retrieve(self.assistant_id)

        self.thread = self.client.beta.threads.create()

        # If a welcome message is provided, add it to the chat history
        if self.welcome_message is not None:
            self.client.beta.threads.messages.create(
                thread_id=self.thread.id,
                role="assistant",
                content=self.welcome_message,
            )
            self.containers.append(
                Container(self, "assistant", blocks=[Block(self, "text", self.welcome_message)])
            )

        # If message files are provided, upload them to the assistant
        if self.message_files is not None:
            for message_file in self.message_files:
                tracked_file = TrackedFile(self, message_file=message_file)
                self.tracked_files.append(tracked_file)

        # If chat history file is provided, load the chat history
        if self.history is not None:
            if not self.history.endswith(".zip"):
                raise ValueError("History file must end with .zip")
            with tempfile.TemporaryDirectory() as t:
                with zipfile.ZipFile(self.history, "r") as f:
                    f.extractall(t)
                with open(f"{t}/{self.history.replace('.zip', '')}/data.json", "r") as f:
                    data = json.load(f)
                    if data["class"] != self.__class__.__name__:
                        raise ValueError(f"Expected class {self.__class__.__name__}, but got {data['class']}")
                    for container in data["containers"]:
                        self.containers.append(Container(
                            self,
                            container["role"],
                            blocks=[Block(self, block["category"], block["content"]) for block in container["blocks"]]
                        ))
                        for block in container["blocks"]:
                            self.client.beta.threads.messages.create(
                                thread_id=self.thread.id,
                                role=container["role"],
                                content=block["content"],
                            )

    @property
    def last_container(self) -> Optional[Container]:
        """Returns the last container or None if empty."""
        return self.containers[-1] if self.containers else None

    def run(self, uploaded_files=None) -> None:
        """Runs the main assistant loop: handles file input and user messages."""
        if self.info_message is not None:
            st.info(self.info_message)
        self.handle_files(uploaded_files)
        for container in self.containers:
            container.write()
        prompt = st.chat_input(placeholder=self.placeholder)
        if prompt:
            with st.chat_message("user"):
                st.markdown(prompt)
            self.containers.append(
                Container(self, "user", blocks=[Block(self, "text", prompt)])
            )
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

    def respond(self, prompt) -> None:
        """Sends the user prompt to the assistant and streams the response."""
        if not self.is_thread_active():
            self.client.beta.threads.messages.create(
                thread_id=self.thread.id,
                role="user",
                content=prompt,
            )
            self.containers.append(Container(self, "assistant"))
            if not self.is_thread_active():
                with self.client.beta.threads.runs.stream(
                    thread_id=self.thread.id,
                    event_handler=AssistantEventHandler(self),
                    assistant_id=self.assistant.id,
                ) as stream:
                    stream.until_done()
        
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

        # Handle file removals
        for tracked_file in self.tracked_files:
            if tracked_file.removed:
                continue
            else:
                if uploaded_files is None:
                    tracked_file.remove()
                elif tracked_file.uploaded_file.file_id not in [x.file_id for x in uploaded_files]:
                    tracked_file.remove()
                else:
                    continue

    def save(self, file_path: str) -> None:
        """Saves the chat history to a ZIP file."""
        if not file_path.endswith(".zip"):
            raise ValueError("File path must end with .zip")
        data = {
            "class": self.__class__.__name__,
            "containers": [container.to_dict() for container in self.containers],
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

    def is_thread_active(self) -> bool:
        """Checks if the thread is active."""
        has_more = True
        after = None
        while has_more:
            response = self.client.beta.threads.runs.list(
                thread_id=self.thread.id,
                limit=100,
                after=after
            )
            for run in response.data:
                if run.status in ["queued", "in_progress", "requires_action", "cancelling"]:
                    return True
            has_more = response.has_more
            if has_more:
                after = response.data[-1].id
        return False

class AssistantEventHandler(openai.AssistantEventHandler):
    """
    Custom event handler for OpenAI Assistant streaming events, designed to 
    manage dynamic updates to the Streamlit chat UI in real time.

    This class listens for various assistant events such as streaming text, 
    tool calls, code execution, image uploads, and function call completions. 
    It updates the corresponding UI container in Streamlit's session state 
    accordingly.

    Attributes:
        chat (Assistants): The Assistants instance that this event handler is associated with.
    """
    def __init__(
        self,
        chat: Assistants,
    ) -> None:
        super().__init__()
        self.chat = chat

    def on_text_delta(self, delta: TextDelta, snapshot: Text) -> None:
        """Handles streaming text output by updating the last container, stripping out annotations."""
        if delta.annotations is not None:
            for annotation in delta.annotations:
                if annotation.type == "file_path":
                    self.chat.last_container.update_and_stream(
                        "download",
                        self.chat.client.files.retrieve(annotation.file_path.file_id)
                    )
        if delta.value is not None and delta.value:
            self.chat.last_container.update_and_stream("text", delta.value)
            self.chat.last_container.last_block.content = re.sub(r"【.*?】", "", self.chat.last_container.last_block.content)
            self.chat.last_container.last_block.content = re.sub(r"\[.*?\]\(sandbox:/mnt/data/.*?\)", "", self.chat.last_container.last_block.content)

    def on_tool_call_delta(self, delta: ToolCallDelta, snapshot: ToolCall) -> None:
        """Handles streaming tool call output, including function names and code interpreter input."""
        if delta.type == "function":
            self.chat.last_container.stream()
        elif delta.type == "code_interpreter":
            if delta.code_interpreter.input:
                self.chat.last_container.update_and_stream("code", delta.code_interpreter.input)

    def on_image_file_done(self, image_file: ImageFile) -> None:
        """Handles image file completion and streams the image to the chat container."""
        image_data = self.chat.client.files.content(image_file.file_id)
        image_data_bytes = image_data.read()
        self.chat.last_container.update_and_stream("image", image_data_bytes)

    def submit_tool_outputs(self, tool_outputs, run_id) -> None:
        """Submits outputs of tool calls back to the assistant and streams the result."""
        with self.chat.client.beta.threads.runs.submit_tool_outputs_stream(
            thread_id=self.current_run.thread_id,
            run_id=self.current_run.id,
            tool_outputs=tool_outputs,
            event_handler=AssistantEventHandler(self.chat),
        ) as stream:
            stream.until_done()

    def handle_requires_action(self, data, run_id) -> None:
        """Resolves required function calls by executing them and preparing the tool outputs."""
        tool_outputs = []
        for tool_call in data.required_action.submit_tool_outputs.tool_calls:
            function = [x for x in self.chat.functions if x.definition["name"] == tool_call.function.name][0]
            result = function.function(**json.loads(tool_call.function.arguments))
            tool_outputs.append({"tool_call_id": tool_call.id, "output": result})
        self.submit_tool_outputs(tool_outputs, run_id)

    def on_event(self, event: AssistantStreamEvent) -> None:
        """General event dispatcher that handles "requires_action" events and triggers function execution."""
        if event.event == "thread.run.requires_action":
            run_id = event.data.id
            self.handle_requires_action(event.data, run_id)

class TrackedFile():
    """
    A class to represent a file that is tracked and managed within the OpenAI and Streamlit integration.

    Attributes:
        chat (Assistants): The Assistants instance that this file is associated with.
        uploaded_file (UploadedFile): The UploadedFile object created by Streamlit.
        message_file (str): The file path of the message file.
        openai_file (File): The File object created by OpenAI for general purposes.
        vision_file (File): The File object created by OpenAI for vision purposes.
        removed (bool): A flag indicating whether the file has been removed.
        file_path (Path): The path to the file on the local filesystem.
    """
    def __init__(
        self,
        chat: Assistants,
        uploaded_file: Optional[UploadedFile] = None,
        message_file: Optional[str] = None,
    ) -> None:
        if (uploaded_file is None) == (message_file is None):
            raise ValueError("Exactly one of 'uploaded_file' or 'message_file' must be provided.")
        self.chat = chat
        self.uploaded_file = uploaded_file
        self.message_file = message_file
        self.openai_file = None
        self.vision_file = None
        self.removed = False

        if self.uploaded_file is not None:
            self.file_path = Path(os.path.join(self.chat.temp_dir.name, self.uploaded_file.name))
            with open(self.file_path, "wb") as f:
                f.write(self.uploaded_file.getvalue())
        else:
            self.file_path = Path(self.message_file).resolve()

        self.chat.client.beta.threads.messages.create(
            thread_id=self.chat.thread.id,
            role="user",    
            content=f"File locally available at: {self.file_path}",
        )
        
        if self.file_path.suffix in VISION_EXTENSIONS:
            self.vision_file = self.chat.client.files.create(file=self.file_path, purpose="vision")
            self.chat.client.beta.threads.messages.create(
                thread_id=self.chat.thread.id,
                role="user",
                content=[
                    {"type": "text", "text": f"Image uploaded to OpenAI: {self.file_path.name}"},
                    {"type": "image_file", "image_file": {"file_id": self.vision_file.id}}
                ]
            )

        if self.vision_file is None and self.chat.tools is None:
            raise ValueError("No tools available for the file: ", self.file_path.name)

        file_tools = []
        upload_to_openai = False
        if self.chat.file_search and self.file_path.suffix in FILE_SEARCH_EXTENSIONS:
            file_tools.append({"type": "file_search"})
            upload_to_openai = True
        if self.chat.code_interpreter and self.file_path.suffix in CODE_INTERPRETER_EXTENSIONS:
            file_tools.append({"type": "code_interpreter"})
            upload_to_openai = True
        if upload_to_openai:
            self.openai_file = self.chat.client.files.create(file=self.file_path, purpose="assistants")
            self.chat.client.beta.threads.messages.create(
                thread_id=self.chat.thread.id,
                role="user",    
                content=f"File uploaded to OpenAI: {self.file_path.name}",
                attachments=[{"file_id": self.openai_file.id, "tools": file_tools}],
            )

    def __repr__(self) -> None:
        return f"TrackedFile(uploaded_file='{self.uploaded_file.name}', deleted={self.removed})"

    def remove(self) -> None:
        if self.openai_file is not None:
            response = self.chat.client.files.delete(self.openai_file.id)
            if not response.deleted:
                raise ValueError("File could not be deleted from OpenAI: ", self.uploaded_file.name)
            self.chat.client.beta.threads.messages.create(
                thread_id=self.chat.thread.id,
                role="user",
                content=f"File removed: {self.uploaded_file.name}",
            )
        if self.vision_file is not None:
            response = self.chat.client.files.delete(self.vision_file.id)
            if not response.deleted:
                raise ValueError("Image could not be deleted from OpenAI: ", self.uploaded_file.name)
            self.chat.client.beta.threads.messages.create(
                thread_id=self.chat.thread.id,
                role="user",
                content=f"Image removed: {self.uploaded_file.name}",
            )
        self.removed = True