import streamlit as st
import openai
import os
from pathlib import Path
from typing import Optional, List
from .utils import Container, Block
from streamlit.runtime.uploaded_file_manager import UploadedFile

DEVELOPER_MESSAGE = """
- Use GitHub-flavored Markdown in your response, including tables, images, URLs, code blocks, and lists.
- Wrap all mathematical expressions and LaTeX terms in `$...$` for inline math and `$$...$$` for display math.
"""

FILE_SEARCH_EXTENSIONS = [
    ".c", ".cpp", ".cs", ".css", ".doc", ".docx", ".go", 
    ".html", ".java", ".js", ".json", ".md", ".pdf", ".php", 
    ".pptx", ".py", ".rb", ".sh", ".tex", ".ts", ".txt"
]

class Responses():
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = "gpt-4o",
        user_avatar: Optional[str] = None,
        assistant_avatar: Optional[str] = None,
        instructions: Optional[str] = None,
        temperature: Optional[float] = 1.0,
        placeholder: Optional[str] = "Your message",
        welcome_message: Optional[str] = None,
        message_files: Optional[List[str]] = None,
        vector_store_ids: Optional[List[str]] = None,
    ) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY") if api_key is None else api_key
        self.model = model
        self.user_avatar = user_avatar
        self.assistant_avatar = assistant_avatar
        self.instructions = "" if instructions is None else instructions
        self.temperature = temperature
        self.placeholder = placeholder
        self.welcome_message = welcome_message
        self.message_files = message_files
        self.vector_store_ids = vector_store_ids
        self.client = openai.OpenAI(api_key=self.api_key)
        self.input = []
        self.containers = []
        self.tools = []
        self.tracked_files = []

        if self.vector_store_ids is not None:
            self.tools.append({"type": "file_search", "vector_store_ids": self.vector_store_ids})

        # If a welcome message is provided, add it to the chat history
        if self.welcome_message is not None:
            self.input.append({"role": "assistant", "content": self.welcome_message})
            self.containers.append(
                Container(self, "assistant", blocks=[Block(self, "text", self.welcome_message)])
            )

        # If message files are provided, upload them to the assistant
        if self.message_files is not None:
            for message_file in self.message_files:
                tracked_file = TrackedFile(self, message_file=message_file)
                self.tracked_files.append(tracked_file)

    @property
    def last_container(self) -> Optional[Container]:
        return self.containers[-1] if self.containers else None

    def respond(self, prompt) -> None:
        self.input.append({"role": "user", "content": prompt})
        self.containers.append(Container(self, "assistant"))
        events = self.client.responses.create(
            model=self.model,
            input=self.input,
            instructions=DEVELOPER_MESSAGE+self.instructions,
            temperature=self.temperature,
            tools=self.tools,
            stream=True,
        )
        response = ""
        for event in events:
            if event.type == "response.output_text.delta":
                self.last_container.update_and_stream("text", event.delta)
                response += event.delta
        self.input.append({"role": "assistant", "content": response})

    def run(self) -> None:
        for container in self.containers:
            container.write()
        prompt = st.chat_input(placeholder=self.placeholder)
        if prompt:
            with st.chat_message("user"):
                st.markdown(prompt)
            self.containers.append(
                Container(self, "user", blocks=[Block(self, "text", prompt)])
            )
            self.respond(prompt)

class TrackedFile():
    def __init__(
        self,
        chat: Responses,
        uploaded_file: Optional[UploadedFile] = None,
        message_file: Optional[str] = None,
    ) -> None:
        if (uploaded_file is None) == (message_file is None):
            raise ValueError("Exactly one of 'uploaded_file' or 'message_file' must be provided.")
        self.chat = chat
        self.uploaded_file = uploaded_file
        self.message_file = message_file
        self.openai_file = None
        self.vector_store = None

        if self.uploaded_file is not None:
            self.file_path = Path(os.path.join(self.chat.temp_dir.name, self.uploaded_file.name))
            with open(self.file_path, "wb") as f:
                f.write(self.uploaded_file.getvalue())
        else:
            self.file_path = Path(self.message_file).resolve()

        self.chat.input.append(
            {"role": "user", "content": [{"type": "input_text", "text": f"File locally available at: {self.file_path}"}]}
        )

        if self.file_path.suffix in FILE_SEARCH_EXTENSIONS:
            with open(self.file_path, "rb") as f:
                self.openai_file = self.chat.client.files.create(file=f, purpose="assistants")
            self.vector_store = self.chat.client.vector_stores.create()
            self.chat.client.vector_stores.files.create(
                vector_store_id=self.vector_store.id,
                file_id=self.openai_file.id
            )
            result = self.chat.client.vector_stores.files.retrieve(
                vector_store_id=self.vector_store.id,
                file_id=self.openai_file.id,
            )
            while result.status != "completed":
                result = self.chat.client.vector_stores.files.retrieve(
                    vector_store_id=self.vector_store.id,
                    file_id=self.openai_file.id,
                )
            if not self.chat.tools:
                self.chat.tools.append({"type": "file_search", "vector_store_ids": [self.vector_store.id]})
            else:
                for tool in self.chat.tools:
                    if tool["type"] == "file_search":
                        if self.vector_store.id not in tool["vector_store_ids"]:
                            tool["vector_store_ids"].append(self.vector_store.id)
                        break
                else:
                    self.chat.tools.append({"type": "file_search", "vector_store_ids": [self.vector_store.id]})

    def __repr__(self) -> None:
        return f"TrackedFile(uploaded_file='{self.file_path.name}')"