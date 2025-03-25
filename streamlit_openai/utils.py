import streamlit as st
import os, tempfile
from pathlib import Path
from streamlit.runtime.uploaded_file_manager import UploadedFile

class Container():
    def __init__(self, role, blocks=None):
        self.delta_generator = st.empty()
        self.role = role
        self.blocks = blocks

    def __repr__(self):
        return f"Container(role='{self.role}', blocks={self.blocks})"

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
        return f"Block('category={self.category}', content='{content}')"

    def iscategory(self, category):
        return self.category == category

    def write(self):        
        if self.category == "text":
            st.markdown(self.content)
        elif self.category == "code":
            st.code(self.content)
        elif self.category == "image":
            st.image(self.content)

class TrackedFile():
    """
    A class to represent a file that is tracked and managed within the OpenAI and Streamlit integration.

    Attributes:
        uploaded_file (UploadedFile): The UploadedFile object created by Streamlit.
        openai_file (File): The File object created by OpenAI.
        removed (bool): A flag indicating whether the file has been removed.
    """
    def __init__(self, uploaded_file: UploadedFile) -> None:
        self.uploaded_file = uploaded_file
        self.openai_file = None
        self.removed = False

    def __repr__(self):
        return f"TrackedFile(uploaded_file='{self.uploaded_file.name}', deleted={self.removed})"

    def to_openai(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            file_path = os.path.join(t, self.uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(self.uploaded_file.getvalue())
            self.openai_file = st.session_state.chat.client.files.create(file=Path(file_path), purpose="assistants")
            st.session_state.chat.client.beta.threads.messages.create(
                thread_id=st.session_state.chat.thread.id,
                role="user",    
                content=f"File uploaded: {self.uploaded_file.name}",
                attachments=[{"file_id": self.openai_file.id, "tools": [{"type": "file_search"}]}]
            )

    def remove(self) -> None:
        response = st.session_state.chat.client.files.delete(self.openai_file.id)
        if not response.deleted:
            raise ValueError("File could not be deleted from OpenAI: ", self.uploaded_file.name)
        st.session_state.chat.client.beta.threads.messages.create(
            thread_id=st.session_state.chat.thread.id,
            role="user",
            content=f"File removed: {self.uploaded_file.name}",
        )
        self.removed = True

class CustomFunction():
    def __init__(self, definition, function) -> None:
        self.definition = definition
        self.function = function