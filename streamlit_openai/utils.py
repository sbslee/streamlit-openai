import streamlit as st
import openai
import os
import json
import tempfile
from pathlib import Path

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

class Chat():
    def __init__(
            self,
            openai_api_key=None,
            model="gpt-4o",
            functions=None,
            file_search=False,
            code_interpreter=False,
    ):
        self.containers = []
        self.current_container = None
        self.functions = functions
        self.tools = None
        self.openai_api_key = None
        self.model = model
        self.client = None
        self.st_files = None
        self.tracked_files = []
        self.file_search = file_search
        self.code_interpreter = code_interpreter
        
        if openai_api_key is None:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
        else:
            self.openai_api_key = openai_api_key

        if self.file_search or self.code_interpreter or self.functions is not None:
            self.tools = []
        if self.file_search:
            self.tools.append({"type": "file_search"})
        if self.code_interpreter:
            self.tools.append({"type": "code_interpreter"})
        if self.functions is not None:
            for function in self.functions:
                self.tools.append({"type": "function", "function": function.definition})

        self.client = openai.OpenAI(api_key=self.openai_api_key)

    def start(self):
        self.handle_files()
        for container in self.containers:
            container.write()
        if prompt := st.chat_input():
            with st.chat_message("user"):
                st.markdown(prompt)
            self.containers.append(
                Container("user", blocks=[Block("text", prompt)])
            )
            self.respond(prompt)

    def get_function(self, name):
        return [x for x in self.functions if x.definition["name"] == name][0]

    def upload_files(self, uploaded_files):
        self.st_files = uploaded_files

    def handle_files(self):
        pass

    def is_tracking(self, st_file):
        return st_file.file_id in [x.st_file.file_id for x in self.tracked_files]
    
class CompletionChat(Chat):
    def __init__(
            self,
            openai_api_key=None,
            model="gpt-4o",
            functions=None,
            file_search=False,
            code_interpreter=False,
    ):
        super().__init__(
            openai_api_key,
            model,
            functions,
            file_search,
            code_interpreter
        )
        self.messages = []

    def _respond1(self):
        chunks = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            stream=True,
        )
        self.messages.append({"role": "assistant", "content": chunks})
        for x in chunks:
            if x.choices[0].delta.content is not None:
                self.current_container.update_and_stream("text", x.choices[0].delta.content)

    def _respond2(self):
        chunks = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            stream=True,
            tools=self.tools,
        )
        self.messages.append({"role": "assistant", "content": chunks})
        current_tool = {}
        used_tools = {}
        for x in chunks:
            if x.choices[0].delta.content is not None:
                self.current_container.update_and_stream("text", x.choices[0].delta.content)
            if x.choices[0].finish_reason == 'tool_calls':
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

                result = self.get_function(tool).function(**json.loads(used_tools[tool]["args"]))
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": used_tools[tool]["id"],
                    "content": result,
                })

            chunks = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                stream=True,
            )
            self.messages.append({"role": "assistant", "content": chunks})

            for x in chunks:
                if x.choices[0].delta.content is not None:
                    self.current_container.update_and_stream("text", x.choices[0].delta.content)
        
    def respond(self, prompt):
        self.current_container = Container("assistant")
        self.messages.append({"role": "user", "content": prompt})
        if self.functions is None:
            self._respond1()
        else:  
            self._respond2()
        self.containers.append(self.current_container)

class AssistantChat(Chat):
    """
    A class to represent an Assistant Chat.

    There are two ways to create an instance of this class:
    1. By providing an `assistant_id`, in which case the class will be created by retrieving an existing assistant from the OpenAI server.
    2. If `assistant_id` is not provided, the class will be created by creating a new assistant.

    Attributes:
        openai_api_key (str): The API key for OpenAI.
        model (str): The model to be used.
        name (str): The name of the assistant.
        assistant_id (str): The ID of the assistant.
        functions (list): The functions to be used.
        file_search (bool): Whether to enable File Search.
    """
    def __init__(
            self,
            openai_api_key=None,
            model="gpt-4o",
            name=None,
            assistant_id=None,
            functions=None,
            file_search=False,
            code_interpreter=False,
    ):
        super().__init__(
            openai_api_key,
            model,
            functions,
            file_search,
            code_interpreter
        )
        self.assistant_id = assistant_id
        self.assistant = None
        self.thread = None
        if self.assistant_id is None:
            self.assistant = self.client.beta.assistants.create(
                name=name,
                model=self.model,
                tools=self.tools,
            )
        else:
            self.assistant = self.client.beta.assistants.retrieve(self.assistant_id)
        self.thread = self.client.beta.threads.create()
 
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

    def handle_files(self):
        if self.st_files is None:
            return

        # Handle file uploads
        for st_file in self.st_files:
            if self.is_tracking(st_file):
                continue
            tracked_file = TrackedFile(st_file)
            tracked_file.to_openai()
            self.tracked_files.append(tracked_file)

        # Handle file removals
        for tracked_file in self.tracked_files:
            if tracked_file.removed:
                continue
            if tracked_file.st_file.file_id not in [x.file_id for x in self.st_files]:
                tracked_file.remove()

class Container():
    def __init__(self, role, blocks=None):
        self.delta_generator = st.empty()
        self.role = role
        self.blocks = blocks

    def __repr__(self):
        return f"Container('{self.role}', {self.blocks})"

    @property
    def empty(self):
        return self.blocks is None

    @property
    def last_block(self):
        return None if self.empty else self.blocks[-1]

    def update(self, category, content):
        if self.empty:
            self.blocks = [Block(category, content)]
        elif self.last_block.iscategory(category):
            self.last_block.content += content
        else:
            self.blocks.append(Block(category, content))

    def write(self):
        if self.empty:
            pass
        else:
            with st.chat_message(self.role):
                for block in self.blocks:
                    block.write()

    def update_and_stream(self, category, content):
        self.update(category, content)
        self.stream()

    def stream(self):
        with self.delta_generator:
            self.write()

class Block():
    def __init__(self, category, content=None):
        self.category = category
        self.content = content

        if self.content is None:
            self.content = ""
        else:
            self.content = content

    def __repr__(self):
        if self.category == "text" or self.category == "code":
            content = self.content
            if len(content) > 50:
                content = content[:30] + "..."
        elif self.category == "image":
            content = "Bytes"
        return f"Block('{self.category}', '{content}')"

    def iscategory(self, category):
        return self.category == category

    def write(self):        
        if self.category == "text":
            st.markdown(self.content)
        elif self.category == "code":
            st.code(self.content)
        elif self.category == "image":
            st.image(self.content)

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
        if event.event == 'thread.run.requires_action':
            run_id = event.data.id
            self.handle_requires_action(event.data, run_id)

class TrackedFile():
    def __init__(self, st_file):
        self.st_file = st_file
        self.openai_file = None
        self.removed = False

    def to_openai(self):
        with tempfile.TemporaryDirectory() as t:
            file_path = os.path.join(t, self.st_file.name)
            with open(file_path, "wb") as f:
                f.write(self.st_file.getvalue())
            self.openai_file = st.session_state.chat.client.files.create(file=Path(file_path), purpose="assistants")
            st.session_state.chat.client.beta.threads.messages.create(
                thread_id=st.session_state.chat.thread.id,
                role="user",    
                content=f"File uploaded: {self.st_file.name}",
                attachments=[{"file_id": self.openai_file.id, "tools": [{"type": "file_search"}]}]
            )

    def remove(self):
        st.session_state.chat.client.files.delete(self.openai_file.id)
        st.session_state.chat.client.beta.threads.messages.create(
            thread_id=st.session_state.chat.thread.id,
            role="user",
            content=f"File removed: {self.st_file.name}",
        )
        self.removed = True