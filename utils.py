import streamlit as st
import openai
import os

class EventHandler(openai.AssistantEventHandler):
    def __init__(self, containers):
        super().__init__()
        self.containers = containers
        self.current_container = Container("assistant")

    def on_text_delta(self, delta, snapshot):
        if self.current_container.empty or not self.current_container.last_block.iscategory("text"):
            self.current_container.add_block(Block("text"))
        self.current_container.last_block.content += delta.value
        self.current_container.write_stream()

    def on_end(self):
        self.containers.append(self.current_container)
        self.current_container = Container("assistant")

class Chat():
    def __init__(self, assistant_id):
        self.client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self.containers = []
        self.assistant_id = assistant_id
        self.assistant = self.client.beta.assistants.retrieve(assistant_id)
        self.thread = self.client.beta.threads.create(
            messages=[{"role": "user", "content": "안녕하세요."}]
        )

    def write(self):
        with self.client.beta.threads.runs.stream(
            thread_id=self.thread.id,
            assistant_id=self.assistant.id,
            event_handler=EventHandler(self.containers),
        ) as stream:
            stream.until_done()

    def add_user_input(self, content):
        with st.chat_message("user"):
            st.markdown(content)
        self.client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=content,
        )
        self.containers.append(
            Container("user", blocks=[Block("text", content)])
        )

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
        for block in self.blocks:
            block.write(self.role)

    def write_stream(self):
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

    def write(self, role):
        with st.chat_message(role):
            if self.category == "text":
                st.markdown(self.content)