import streamlit as st
import openai
import os, json, tempfile
from typing import Optional
from .utils import Container, Block, TrackedFile

SUPPORTED_FILES = {
    "file_search": [
        ".c", ".cs", ".cpp", ".doc", ".docx", ".html", ".java", 
        ".json", ".md", ".pdf", ".php", ".pptx", ".py", ".rb", 
        ".texv", ".txt", ".css", ".js", ".sh", ".ts"
    ],
    "code_interpreter": [
        ".c", ".cs", ".cpp", ".doc", ".docx", ".html", ".java", 
        ".json", ".md", ".pdf", ".php", ".pptx", ".py", ".rb", 
        ".tex", ".txt", ".css", ".js", ".sh", ".ts", ".csv", ".jpeg", 
        ".jpg", ".gif", ".png", ".tar", ".xlsx", ".xml", ".zip"
    ]
}

class Assistants():
    """
    A class to represent an Assistant Chat.

    There are two ways to create an instance of this class:
    1. By providing an `assistant_id`, in which case the class will be created by retrieving an existing assistant from the OpenAI server.
    2. If `assistant_id` is not provided, the class will be created by creating a new assistant.

    Attributes:
        api_key (str): The API key for OpenAI.
        model (str): The model to be used.
        name (str): The name of the assistant.
        assistant_id (str): The ID of the assistant.
        functions (list): The functions to be used.
        file_search (bool): Whether to enable File Search.
        code_interpreter (bool): Whether to enable Code Interpreter.
    """
    def __init__(
            self,
            api_key: Optional[str] = None,
            model: str = "gpt-4o",
            name=None,
            assistant_id=None,
            functions=None,
            file_search: bool = False,
            code_interpreter: bool = False,
    ):
        self.api_key = os.getenv("OPENAI_API_KEY") if api_key is None else api_key
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = model
        self.containers = []
        self.current_container = None
        self.functions = functions
        self.tools = None
        self.tracked_files = []
        self.file_search = file_search
        self.code_interpreter = code_interpreter
        self.assistant_id = assistant_id
        self.assistant = None
        self.thread = None

        if self.file_search or self.code_interpreter or self.functions is not None:
            self.tools = []
        if self.file_search:
            self.tools.append({"type": "file_search"})
        if self.code_interpreter:
            self.tools.append({"type": "code_interpreter"})
        if self.functions is not None:
            for function in self.functions:
                self.tools.append({"type": "function", "function": function.definition})

        if self.assistant_id is None:
            self.assistant = self.client.beta.assistants.create(
                name=name,
                model=self.model,
                tools=self.tools,
            )
        else:
            self.assistant = self.client.beta.assistants.retrieve(self.assistant_id)
        self.thread = self.client.beta.threads.create()
 
    def run(self, uploaded_files=None):
        self.handle_files(uploaded_files)
        for container in self.containers:
            container.write()
        if prompt := st.chat_input():
            with st.chat_message("user"):
                st.markdown(prompt)
            self.containers.append(
                Container("user", blocks=[Block("text", prompt)])
            )
            self.respond(prompt)

    def respond(self, prompt):
        self.current_container = Container("assistant")
        self.client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=prompt,
        )
        with self.client.beta.threads.runs.stream(
            thread_id=self.thread.id,
            event_handler=EventHandler(),
            assistant_id=self.assistant.id,
        ) as stream:
            stream.until_done()
        self.containers.append(self.current_container)

    def handle_files(self, uploaded_files) -> None:
        # Handle file uploads
        if uploaded_files is None:
            return
        else:
            for uploaded_file in uploaded_files:
                if self.is_tracking(uploaded_file):
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

    def get_function(self, name):
        return [x for x in self.functions if x.definition["name"] == name][0]

    def handle_files(self, uploaded_files) -> None:
        pass

    def is_tracking(self, uploaded_file):
        return uploaded_file.file_id in [x.uploaded_file.file_id for x in self.tracked_files]

class EventHandler(openai.AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.current_container = st.session_state.chat.current_container

    def on_text_delta(self, delta, snapshot):
        if delta.value:
            self.current_container.update_and_stream("text", delta.value)

    def on_tool_call_delta(self, delta, snapshot):
        if delta.type == "function":
            self.current_container.stream()
        elif delta.type == "code_interpreter":
            if delta.code_interpreter.input:
                self.current_container.update_and_stream("code", delta.code_interpreter.input)

    def on_image_file_done(self, image_file):
        image_data = st.session_state.chat.client.files.content(image_file.file_id)
        image_data_bytes = image_data.read()
        self.current_container.update_and_stream("image", image_data_bytes)

    def submit_tool_outputs(self, tool_outputs, run_id):
        with st.session_state.chat.client.beta.threads.runs.submit_tool_outputs_stream(
            thread_id=self.current_run.thread_id,
            run_id=self.current_run.id,
            tool_outputs=tool_outputs,
            event_handler=EventHandler(),
        ) as stream:
            stream.until_done()

    def handle_requires_action(self, data, run_id):
        tool_outputs = []
        for tool in data.required_action.submit_tool_outputs.tool_calls:
            result = st.session_state.chat.get_function(tool.function.name).function(**json.loads(tool.function.arguments))
            tool_outputs.append({"tool_call_id": tool.id, "output": result})
        self.submit_tool_outputs(tool_outputs, run_id)

    def on_event(self, event):
        if event.event == "thread.run.requires_action":
            run_id = event.data.id
            self.handle_requires_action(event.data, run_id)