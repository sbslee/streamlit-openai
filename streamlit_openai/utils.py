import openai
import streamlit as st
import os, tempfile
from pathlib import Path
from typing import Optional, List, Union, Callable, Dict, Any
from streamlit.runtime.uploaded_file_manager import UploadedFile

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

class Block():
    """
    Represents a single unit of content in a chat interface—such as text, 
    code, an image, or a downloadable file.

    A `Block` encapsulates and renders various types of messages within the 
    chat UI. It associates the content with its category (e.g., text, code, 
    image, or download) and includes the logic required for proper display and 
    interaction.

    Attributes:
        category (str): The type of content ('text', 'code', 'image', or 'download').
        content (str, bytes, or openai.File): The actual content of the block. This can be a string for text or code, bytes for images, or an `openai.File` object for downloadable files.
    """
    def __init__(
            self,
            category: str,
            content: Optional[Union[str, bytes, openai.File]] = None,
    ) -> None:
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
        """Renders the block's content to the Streamlit interface."""
        if self.category == "text":
            st.markdown(self.content)
        elif self.category == "code":
            st.code(self.content)
        elif self.category == "image":
            st.image(self.content)
        elif self.category == "download":
            filename = os.path.basename(self.content.filename)
            _, file_extension = os.path.splitext(filename)
            st.download_button(
                label=filename,
                data=st.session_state.chat.client.files.content(self.content.id).read(),
                file_name=filename,
                mime=MIME_TYPES[file_extension.lstrip(".")],
                icon=":material/download:",
                key=st.session_state.chat.download_button_key,
            )
            st.session_state.chat.download_button_key += 1

class Container():
    """
    Represents a single message container in a Streamlit chat interface, 
    managing role-based message blocks and real-time updates.

    This class holds a sequence of message blocks (e.g., text, code, image) 
    associated with a role (e.g., "user", "assistant"), and handles updating, 
    rendering, and streaming content to the UI.

    Attributes:
        delta_generator: A Streamlit placeholder used for dynamic content updates.
        role (str): The role associated with this message (e.g., "user" or "assistant").
        blocks (list): A list of Block instances representing message segments.
    """
    def __init__(
            self,
            role: str,
            blocks: Optional[List[Block]] = None,
    ) -> None:
        self.delta_generator = st.empty()
        self.role = role
        self.blocks = blocks

    def __repr__(self) -> None:
        return f"Container(role='{self.role}', blocks={self.blocks})"

    @property
    def empty(self) -> bool:
        """Returns True if the container has no blocks."""
        return self.blocks is None

    @property
    def last_block(self) -> Optional[Block]:
        """Returns the last block in the container or None if empty."""
        return None if self.empty else self.blocks[-1]

    def update(self, category, content) -> None:
        """Updates the container with new content, appending or extending existing blocks."""
        if self.empty:
            self.blocks = [Block(category, content)]
        elif category in ["text", "code"] and self.last_block.iscategory(category):
            self.last_block.content += content
        else:
            self.blocks.append(Block(category, content))

    def write(self) -> None:
        """Renders the container's content in the Streamlit chat interface."""
        if self.empty:
            pass
        else:
            with st.chat_message(self.role, avatar=st.session_state.chat.user_avatar if self.role == "user" else st.session_state.chat.assistant_avatar):
                for block in self.blocks:
                    block.write()

    def update_and_stream(self, category, content) -> None:
        """Updates the container and streams the update live to the UI."""
        self.update(category, content)
        self.stream()

    def stream(self) -> None:
        """Renders the container content using Streamlit's delta generator."""
        with self.delta_generator:
            self.write()

class TrackedFile():
    """
    A class to represent a file that is tracked and managed within the OpenAI and Streamlit integration.

    Attributes:
        uploaded_file (UploadedFile): The UploadedFile object created by Streamlit.
        openai_file (File): The File object created by OpenAI.
        removed (bool): A flag indicating whether the file has been removed.
    """
    def __init__(
            self,
            uploaded_file: UploadedFile
    ) -> None:
        self.uploaded_file = uploaded_file
        self.openai_file = None
        self.removed = False

    def __repr__(self) -> None:
        return f"TrackedFile(uploaded_file='{self.uploaded_file.name}', deleted={self.removed})"

    def to_openai(self) -> None:
        if st.session_state.chat.__class__.__name__ == "ChatCompletions":
            with tempfile.TemporaryDirectory() as t:
                file_path = os.path.join(t, self.uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(self.uploaded_file.getvalue())
                self.openai_file = st.session_state.chat.client.files.create(file=Path(file_path), purpose="user_data")
                st.session_state.chat.messages.append(
                    {"role": "user",
                     "content": [
                         {"type": "file", "file": {"file_id": self.openai_file.id}},
                         {"type": "text", "text": f"File uploaded: {os.path.basename(file_path)})"}
                     ]}
                )
        else:
            tools = []
            if st.session_state.chat.file_search:
                tools.append({"type": "file_search"})
            if st.session_state.chat.code_interpreter:
                tools.append({"type": "code_interpreter"})
            with tempfile.TemporaryDirectory() as t:
                file_path = os.path.join(t, self.uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(self.uploaded_file.getvalue())
                self.openai_file = st.session_state.chat.client.files.create(file=Path(file_path), purpose="assistants")
                st.session_state.chat.client.beta.threads.messages.create(
                    thread_id=st.session_state.chat.thread.id,
                    role="user",    
                    content=f"File uploaded: {self.uploaded_file.name}",
                    attachments=[{"file_id": self.openai_file.id, "tools": tools}],
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
    """
    Represents a user-defined function and its corresponding OpenAI function 
    definition.

    This class wraps a callable Python function with metadata in the format 
    expected by OpenAI's function-calling tools.

    Attributes:
        definition (dict): The OpenAI-compatible function schema/definition.
        function (Callable): The actual Python function to be executed when invoked.
    """
    def __init__(
            self,
            definition: Dict[str, Any],
            function: Callable,
    ) -> None:
        self.definition = definition
        self.function = function

    def __repr__(self) -> None:
        return f"CustomFunction(definition='{self.definition}')"