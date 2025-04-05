import streamlit as st
import openai
import os, json, re
from pathlib import Path
from typing import Optional, List
from .utils import Container, Block, TrackedFile, CustomFunction
from openai.types.beta import AssistantStreamEvent
from openai.types.beta.threads import Text, TextDelta, ImageFile
from openai.types.beta.threads.runs import ToolCall, ToolCallDelta

DEVELOPER_MESSAGE = """
- Use GitHub-flavored Markdown in your response, including tables, images, URLs, code blocks, and lists.
- Wrap all mathematical expressions and LaTeX terms in `$...$` for inline math and `$$...$$` for display math.
- All hyperlinks to `sandbox:/mnt/data/*` files must be placed at the end of the message. When you output multiple sandbox hyperlinks, do not use bullets, numbers, or any kind of list formatting. Instead, separate each hyperlink with a blank line, like in a paragraph break.
"""

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
        containers (list): List to track the conversation history in structured form.
        tools (list): Tools (custom functions, file search, code interpreter) enabled for the assistant.
        tracked_files (list): List of files being tracked for uploads/removals.
        assistant (Assistant): The instantiated or retrieved OpenAI assistant.
        thread (Thread): The conversation thread associated with the assistant.
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
        self.assistant_avatar = assistant_avatar
        self.assistant_id = assistant_id
        self.assistant = None
        self.thread = None
        self.download_button_key = 0

        if self.file_search or self.code_interpreter or self.functions is not None:
            self.tools = []
        if self.file_search:
            self.tools.append({"type": "file_search"})
        if self.code_interpreter:
            self.tools.append({"type": "code_interpreter"})
        if self.functions is not None:
            for function in self.functions:
                self.tools.append({"type": "function", "function": function.definition})

        # Create or retrieve the assistant
        if self.assistant_id is None:
            self.assistant = self.client.beta.assistants.create(
                name=name,
                instructions=DEVELOPER_MESSAGE+self.instructions,
                model=self.model,
                tools=self.tools,
                temperature=self.temperature,
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
                Container("assistant", blocks=[Block("text", self.welcome_message)])
            )

        # If message files are provided, upload them to the assistant
        if self.message_files is not None:
            for message_file in self.message_files:
                openai_file = self.client.files.create(file=Path(message_file), purpose="assistants")
                self.client.beta.threads.messages.create(
                    thread_id=self.thread.id,
                    role="user",    
                    content=f"File uploaded: {os.path.basename(message_file)})",
                    attachments=[{"file_id": openai_file.id, "tools": self.tools}],
                )

    @property
    def last_container(self) -> Optional[Container]:
        """Returns the last container or None if empty."""
        return self.containers[-1] if self.containers else None

    def run(self, uploaded_files=None) -> None:
        """Runs the main assistant loop: handles file input and user messages."""
        self.handle_files(uploaded_files)
        for container in self.containers:
            container.write()
        if prompt := st.chat_input(placeholder=self.placeholder):
            with st.chat_message("user"):
                st.markdown(prompt)
            self.containers.append(
                Container("user", blocks=[Block("text", prompt)])
            )
            self.respond(prompt)

    def respond(self, prompt) -> None:
        """Sends the user prompt to the assistant and streams the response."""
        self.containers.append(Container("assistant"))
        self.client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=prompt,
        )
        with self.client.beta.threads.runs.stream(
            thread_id=self.thread.id,
            event_handler=AssistantEventHandler(),
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
                tracked_file = TrackedFile(uploaded_file)
                tracked_file.to_openai()
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

class AssistantEventHandler(openai.AssistantEventHandler):
    """
    Custom event handler for OpenAI Assistant streaming events, designed to 
    manage dynamic updates to the Streamlit chat UI in real time.

    This class listens for various assistant events such as streaming text, 
    tool calls, code execution, image uploads, and function call completions. 
    It updates the corresponding UI container in Streamlit's session state 
    accordingly.
    """
    def __init__(self) -> None:
        super().__init__()
        self.last_container = st.session_state.chat.last_container

    def on_text_delta(self, delta: TextDelta, snapshot: Text) -> None:
        """Handles streaming text output by updating the last container, stripping out annotations."""
        if delta.annotations is not None:
            for annotation in delta.annotations:
                if annotation.type == "file_path":
                    self.last_container.update_and_stream(
                        "download",
                        st.session_state.chat.client.files.retrieve(annotation.file_path.file_id)
                    )
        if delta.value is not None:
            self.last_container.update_and_stream("text", delta.value)
            self.last_container.last_block.content = re.sub(r"【.*?】", "", self.last_container.last_block.content)
            self.last_container.last_block.content = re.sub(r"\[.*?\]\(sandbox:/mnt/data/.*?\)", "", self.last_container.last_block.content)

    def on_tool_call_delta(self, delta: ToolCallDelta, snapshot: ToolCall) -> None:
        """Handles streaming tool call output, including function names and code interpreter input."""
        if delta.type == "function":
            self.last_container.stream()
        elif delta.type == "code_interpreter":
            if delta.code_interpreter.input:
                self.last_container.update_and_stream("code", delta.code_interpreter.input)

    def on_image_file_done(self, image_file: ImageFile) -> None:
        """Handles image file completion and streams the image to the chat container."""
        image_data = st.session_state.chat.client.files.content(image_file.file_id)
        image_data_bytes = image_data.read()
        self.last_container.update_and_stream("image", image_data_bytes)

    def submit_tool_outputs(self, tool_outputs, run_id) -> None:
        """Submits outputs of tool calls back to the assistant and streams the result."""
        with st.session_state.chat.client.beta.threads.runs.submit_tool_outputs_stream(
            thread_id=self.current_run.thread_id,
            run_id=self.current_run.id,
            tool_outputs=tool_outputs,
            event_handler=AssistantEventHandler(),
        ) as stream:
            stream.until_done()

    def handle_requires_action(self, data, run_id) -> None:
        """Resolves required function calls by executing them and preparing the tool outputs."""
        tool_outputs = []
        for tool_call in data.required_action.submit_tool_outputs.tool_calls:
            function = [x for x in st.session_state.chat.functions if x.definition["name"] == tool_call.function.name][0]
            result = function.function(**json.loads(tool_call.function.arguments))
            tool_outputs.append({"tool_call_id": tool_call.id, "output": result})
        self.submit_tool_outputs(tool_outputs, run_id)

    def on_event(self, event: AssistantStreamEvent) -> None:
        """General event dispatcher that handles "requires_action" events and triggers function execution."""
        if event.event == "thread.run.requires_action":
            run_id = event.data.id
            self.handle_requires_action(event.data, run_id)