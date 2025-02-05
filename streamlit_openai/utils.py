import streamlit as st
import openai
import os

class Chat():
    def __init__(self, openai_api_key=None):
        self.containers = []
        self.openai_api_key = None
        self.client = None
        if openai_api_key is None:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
        else:
            self.openai_api_key = openai_api_key
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

class BasicChat(Chat):
    def __init__(
            self,
            openai_api_key=None,
            model="gpt-4o",
    ):
        super().__init__(openai_api_key)
        self.messages = []
        self.model = model

    def respond(self, prompt):
        self.messages.append({"role": "user", "content": prompt})
        current_container = Container("assistant")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in self.messages
            ],
            stream=True,
        )
        if current_container.empty or not current_container.last_block.iscategory("text"):
            current_container.add_block(Block("text"))
        for chunk in response:
            value = chunk.choices[0].delta.content
            if value is not None:
                current_container.last_block.content += value
                current_container.stream()
        self.containers.append(current_container)
        self.messages.append({"role": "assistant", "content": response})

class AssistantChat(Chat):
    def __init__(
            self,
            openai_api_key=None,
            assistant_id=None,
    ):
        super().__init__(openai_api_key)
        self.assistant_id = None
        self.assistant = None
        self.thread = None
        self.assistant_id = assistant_id
        if self.assistant_id is None:
            self.assistant = None
        else:
            self.assistant = self.client.beta.assistants.retrieve(self.assistant_id)
        self.thread = self.client.beta.threads.create()
 
    def respond(self, prompt):
        self.client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=prompt,
        )
        with self.client.beta.threads.runs.stream(
            thread_id=self.thread.id,
            event_handler=EventHandler(self.containers),
            assistant_id=self.assistant.id,
        ) as stream:
            stream.until_done()

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

    def write(self, role):
        with st.chat_message(role):
            if self.category == "text":
                st.markdown(self.content)

class EventHandler(openai.AssistantEventHandler):
    def __init__(self, containers):
        super().__init__()
        self.containers = containers
        self.current_container = Container("assistant")

    def on_text_delta(self, delta, snapshot):
        if self.current_container.empty or not self.current_container.last_block.iscategory("text"):
            self.current_container.add_block(Block("text"))
        self.current_container.last_block.content += delta.value
        self.current_container.stream()

    def on_end(self):
        self.containers.append(self.current_container)
        self.current_container = Container("assistant")