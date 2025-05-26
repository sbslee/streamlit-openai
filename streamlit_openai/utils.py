import openai
import streamlit as st
import os
from typing import Optional, List, Union, Callable, Dict, Any

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
        chat (ChatCompletions or Assistants): The parent chat object managing the chat interface.
        category (str): The type of content ('text', 'code', 'image', or 'download').
        content (str, bytes, or openai.File): The actual content of the block. This can be a string for text or code, bytes for images, or an `openai.File` object for downloadable files.
    """
    def __init__(
            self,
            chat: Union["ChatCompletions", "Assistants"],
            category: str,
            content: Optional[Union[str, bytes, openai.File]] = None,
    ) -> None:
        self.chat = chat
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
                data=self.chat.client.files.content(self.content.id).read(),
                file_name=filename,
                mime=MIME_TYPES[file_extension.lstrip(".")],
                icon=":material/download:",
                key=self.chat.download_button_key,
            )
            self.chat.download_button_key += 1

    def to_dict(self) -> Dict[str, Any]:
        """Converts the block to a dictionary representation."""
        if self.category in ["text", "code"]:
            content = self.content
        elif self.category == "image":
            content = "Bytes"
        elif self.category == "download":
            content = f"File(filename='{os.path.basename(self.content.filename)}')"
        return {
            "category": self.category,
            "content": content,
        }

class Container():
    """
    Represents a single message container in a Streamlit chat interface, 
    managing role-based message blocks and real-time updates.

    This class holds a sequence of message blocks (e.g., text, code, image) 
    associated with a role (e.g., "user", "assistant"), and handles updating, 
    rendering, and streaming content to the UI.

    Attributes:
        chat (ChatCompletions or Assistants): The parent chat object managing the chat interface.
        role (str): The role associated with this message (e.g., "user" or "assistant").
        blocks (list): A list of Block instances representing message segments.
        delta_generator (DeltaGenerator): A Streamlit placeholder used for dynamic content updates.
    """
    def __init__(
            self,
            chat: Union["ChatCompletions", "Assistants"],
            role: str,
            blocks: Optional[List[Block]] = None,
    ) -> None:
        self.chat = chat
        self.role = role
        self.blocks = blocks
        self.delta_generator = st.empty()
        
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
            self.blocks = [Block(self.chat, category, content)]
        elif category in ["text", "code"] and self.last_block.iscategory(category):
            self.last_block.content += content
        else:
            self.blocks.append(Block(self.chat, category, content))

    def write(self) -> None:
        """Renders the container's content in the Streamlit chat interface."""
        if self.empty:
            pass
        else:
            with st.chat_message(self.role, avatar=self.chat.user_avatar if self.role == "user" else self.chat.assistant_avatar):
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

    def to_dict(self) -> Dict[str, Any]:
        """Converts the container to a dictionary representation."""
        if self.empty:
            return {}
        else:
            return {
                "role": self.role,
                "blocks": [block.to_dict() for block in self.blocks],
            }

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