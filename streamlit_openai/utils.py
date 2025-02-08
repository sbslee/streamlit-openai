import streamlit as st
import openai
import os
import json

class Chat():
    def __init__(
            self,
            openai_api_key=None,
            model="gpt-4o",
            functions=None,
    ):
        self.containers = []
        self.current_container = None
        self.functions = functions
        self.tools = None
        self.openai_api_key = None
        self.model = model
        self.client = None
        self.uploaded_files = None
        
        if openai_api_key is None:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
        else:
            self.openai_api_key = openai_api_key
  
        if self.functions is not None:
            self.tools = []
            for function in self.functions:
                self.tools.append({"type": "function", "function": function.definition})
  
        self.client = openai.OpenAI(api_key=self.openai_api_key)

    def start(self):
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
        self.uploaded_files = uploaded_files

class BasicChat(Chat):
    def __init__(
            self,
            openai_api_key=None,
            model="gpt-4o",
            functions=None,
    ):
        super().__init__(openai_api_key, model, functions)
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
                if self.current_container.empty or not self.current_container.last_block.iscategory("text"):
                    self.current_container.add_block(Block("text"))
                self.current_container.last_block.content += x.choices[0].delta.content
            self.current_container.stream()

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
                if self.current_container.empty or not self.current_container.last_block.iscategory("text"):
                    self.current_container.add_block(Block("text"))
                self.current_container.last_block.content += x.choices[0].delta.content
            self.current_container.stream()
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
                    if self.current_container.empty or not self.current_container.last_block.iscategory("text"):
                        self.current_container.add_block(Block("text"))
                    self.current_container.last_block.content += x.choices[0].delta.content
            self.current_container.stream()
        

    def respond(self, prompt):
        self.current_container = Container("assistant")
        self.messages.append({"role": "user", "content": prompt})
        if self.functions is None:
            self._respond1()
        else:  
            self._respond2()
        self.containers.append(self.current_container)

class AssistantChat(Chat):
    def __init__(
            self,
            openai_api_key=None,
            model="gpt-4o",
            assistant_id=None,
            functions=None,
    ):
        super().__init__(openai_api_key, model, functions)
        self.assistant_id = assistant_id
        self.assistant = None
        self.thread = None
        if self.assistant_id is None:
            self.assistant = self.client.beta.assistants.create(
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

class Container():
    def __init__(self, role, blocks=None):
        self.container = st.empty()
        self.role = role
        self.blocks = blocks

    @property
    def empty(self):
        return self.blocks is None

    @property
    def last_block(self):
        return None if self.empty else self.blocks[-1]

    def add_block(self, block):
        if self.empty:
            self.blocks = [block]
        else:
            self.blocks.append(block)

    def write(self):
        if self.empty:
            pass
        else:
            with st.chat_message(self.role):
                for block in self.blocks:
                    block.write()

    def stream(self):
        with self.container:
            self.write()

class Block():
    def __init__(self, category, content=None):
        self.category = category
        self.content = content

        if self.content is None:
            self.content = ""
        else:
            self.content = content

    def iscategory(self, category):
        return self.category == category

    def write(self):        
        if self.category == "text":
            st.markdown(self.content)

class EventHandler(openai.AssistantEventHandler):
    def __init__(self):
        super().__init__()

    def on_text_delta(self, delta, snapshot):
        if st.session_state.chat.current_container.empty or not st.session_state.chat.current_container.last_block.iscategory("text"):
            st.session_state.chat.current_container.add_block(Block("text"))
        st.session_state.chat.current_container.last_block.content += delta.value
        st.session_state.chat.current_container.stream()

    def on_tool_call_delta(self, delta, snapshot):
        if delta.type == "function":
            st.session_state.chat.current_container.stream()

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
