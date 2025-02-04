import streamlit as st
import openai
import os

class EventHandler(openai.AssistantEventHandler):
    def __init__(self):
        super().__init__()

    def on_text_delta(self, delta, snapshot):
        if self.container is None:
            self.container = Container("assistant")
        if not self.container.blocks or self.container.blocks[-1]['type'] != 'text':
            self.container.blocks.append({'type': 'text', 'content': ""})
        if self.show_quotation_marks:
            if delta.annotations is not None:
                for annotation in delta.annotations:
                    if annotation.type == "file_citation":
                        file = st.session_state.client.files.retrieve(annotation.file_citation.file_id)
                        delta.value = delta.value.replace(annotation.text, f"""<a href="#" title="{file.filename}">[❞]</a>""")
                    elif annotation.type == "file_path":
                        file = st.session_state.client.files.retrieve(annotation.file_path.file_id)
                        content = st.session_state.client.files.content(file.id)
                        filename = os.path.basename(file.filename)
                        self.container.code_interpreter_files[filename] = content.read()
            self.container.blocks[-1]["content"] += delta.value

class Chat():
    def __init__(self, assistant_id):
        self.client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self.containers = []
        self.assistant_id = assistant_id
        self.assistant = self.client.beta.assistants.retrieve(assistant_id)
        self.thread = self.client.beta.threads.create(
            messages=[{"role": "user", "content": "안녕하세요."}]
        )
        self.event_handler = EventHandler()

    def write(self):
        with self.client.beta.threads.runs.stream(
            thread_id=self.thread.id,
            assistant_id=self.assistant.id,
            event_handler=self.event_handler,
        ) as stream:
            stream.until_done()

class Container():
    def __init__(self, role, blocks=None):
        self.container = st.empty()
        self.role = role
        self.blocks = blocks

    def write(self):
        for block in self.blocks:
            block.write()

class Block():
    def __init__(self, category, content):
        self.category = category
        self.content = content

    def write(self):
        if self.category == "text":
            st.markdown(self.content)