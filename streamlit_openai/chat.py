import streamlit as st
import openai
import os, json, re, tempfile, zipfile, time, base64, shutil
from pathlib import Path
from typing import Optional, List, Union, Literal, Dict, Any
from .utils import CustomFunction, RemoteMCP
from streamlit.runtime.uploaded_file_manager import UploadedFile

DEVELOPER_MESSAGE = """
- Use GitHub-flavored Markdown in your response, including tables, images, URLs, code blocks, and lists.
- Wrap all mathematical expressions and LaTeX terms in `$...$` for inline math and `$$...$$` for display math.
- When a custom function is called with a file path as its input, you must use the local file path.
"""

CHAT_HISTORY_INSTRUCTIONS = """
- This conversation was loaded from a chat history file.
- All input files uploaded so far were actually provided previously, so you should not treat them as new uploads.
"""

CODE_INTERPRETER_EXTENSIONS = [
    ".c", ".cs", ".cpp", ".csv", ".doc", ".docx", ".html", 
    ".java", ".json", ".md", ".pdf", ".php", ".pptx", ".py", 
    ".rb", ".tex", ".txt", ".css", ".js", ".sh", ".ts", ".csv", 
    ".jpeg", ".jpg", ".gif", ".pkl", ".png", ".tar", ".xlsx", 
    ".xml", ".zip"
]

FILE_SEARCH_EXTENSIONS = [
    ".c", ".cpp", ".cs", ".css", ".doc", ".docx", ".go", 
    ".html", ".java", ".js", ".json", ".md", ".pdf", ".php", 
    ".pptx", ".py", ".rb", ".sh", ".tex", ".ts", ".txt"
]

VISION_EXTENSIONS = [".png", ".jpeg", ".jpg", ".webp", ".gif"]

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
    "xls" : "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "doc" : "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "ppt" : "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

SUMMARY_INSTRUCTIONS = """
- Your task is to provide a very concise summary of the conversation history provided by the user.
- The summary must be in English, four words or fewer.
- Do not include a period at the end of the summary.
- Use title case for the summary.
- If the conversation history lacks enough context to summarize (for example, if it only includes greetings such as “Hi” or “How can I help you today?”), return "New Chat".
- If the conversation is not in English, the summary must be in the same language. For example, if the conversation is in Korean (e.g., "미국 여행 계획을 도와주세요."), return a summary in Korean (e.g., "미국 여행 계획"). The only exception is when the conversation is new and has no meaningful context, in which case you should return "New Chat" in English. Never return "New Chat" in any other language (e.g., "새로운 대화").
- The special keyword "New Chat" indicates that the conversation is new and has no meaningful context. Always return "New Chat" in English, even if the conversation itself is in another language.
"""

class Chat():
    """A Streamlit-based chat interface powered by OpenAI's Responses API."""
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = "gpt-4o",
        instructions: Optional[str] = None,
        temperature: Optional[float] = 1.0,
        accept_file: Union[bool, Literal["multiple"]] = "multiple",
        uploaded_files: Optional[List[str]] = None,
        functions: Optional[List[CustomFunction]] = None,
        mcps: Optional[List[RemoteMCP]] = None,
        user_avatar: Optional[str] = None,
        assistant_avatar: Optional[str] = None,
        placeholder: Optional[str] = "Your message",
        welcome_message: Optional[str] = None,
        example_messages: Optional[List[dict]] = None,
        info_message: Optional[str] = None,
        vector_store_ids: Optional[List[str]] = None,
        allow_code_interpreter: Optional[bool] = True,
        allow_file_search: Optional[bool] = True,
        allow_web_search: Optional[bool] = True,
        allow_image_generation: Optional[bool] = True,
    ) -> None:
        """
        Initializes a Chat instance.

        Args:
            api_key (str): API key for OpenAI. If not provided, fetched from environment variable `OPENAI_API_KEY`.
            model (str): The OpenAI model to use (default: "gpt-4o").
            instructions (str): Instructions for the assistant.
            temperature (float): Sampling temperature for the model (default: 1.0).
            accept_file (bool or str): Whether the chat input should accept files (True, False, or "multiple") (default: "multiple").
            uploaded_files (list): List of files to be uploaded to the assistant during initialization.
            functions (list): List of custom functions to be attached to the assistant.
            mcps (list): List of RemoteMCP objects for using remote Model Context Protocol (MPC) servers.
            user_avatar (str): An emoji, image URL, or file path that represents the user.
            assistant_avatar (str): An emoji, image URL, or file path that represents the assistant.
            placeholder (str): Placeholder text for the chat input box (default: "Your message").
            welcome_message (str): Welcome message from the assistant.
            example_messages (list): List of example messages for the user to choose from.
            info_message (str): Information message to be displayed in the chat. This message is constantly displayed at the top of the chat interface.
            vector_store_ids (list): List of vector store IDs for file search. Only used if file search is enabled. Maximum of two vector stores allowed.
            allow_code_interpreter (bool): Whether to allow code interpreter functionality (default: True).
            allow_file_search (bool): Whether to allow file search functionality (default: True).
            allow_web_search (bool): Whether to allow web search functionality (default: True).
            allow_image_generation (bool): Whether to allow image generation functionality (default: True).
        """
        self.api_key = os.getenv("OPENAI_API_KEY") if api_key is None else api_key
        self.model = model
        self.instructions = "" if instructions is None else instructions
        self.temperature = temperature
        self.accept_file = accept_file
        self.uploaded_files = uploaded_files
        self.functions = functions
        self.mcps = mcps
        self.user_avatar = user_avatar
        self.assistant_avatar = assistant_avatar
        self.placeholder = placeholder
        self.welcome_message = welcome_message
        self.example_messages = example_messages
        self.info_message = info_message
        self.vector_store_ids = vector_store_ids
        self.allow_code_interpreter = allow_code_interpreter
        self.allow_file_search = allow_file_search
        self.allow_web_search = allow_web_search
        self.allow_image_generation = allow_image_generation
        self.summary = "New Chat"
        self.input_tokens = 0
        self.output_tokens = 0
        self._client = openai.OpenAI(api_key=self.api_key)
        self._temp_dir = tempfile.TemporaryDirectory()
        self._selected_example = None
        self._input = []
        self._tools = []
        self._previous_response_id = None
        self._container_id = None
        self._sections = []
        self._static_files = []
        self._tracked_files = []
        self._download_button_key = 0
        self._dynamic_vector_store = None

        if self.allow_web_search:
            self._tools.append({"type": "web_search"})

        if self.allow_image_generation:
            self._tools.append({"type": "image_generation", "partial_images": 3})

        if self.allow_code_interpreter:
            container = self._client.containers.create(name="streamlit-openai")
            self._container_id = container.id
            self._tools.append({"type": "code_interpreter", "container": self._container_id})

        if self.functions is not None:
            for function in self.functions:
                self._tools.append({
                    "type": "function",
                    "name": function.name,
                    "description": function.description,
                    "parameters": function.parameters,
                })

        if self.mcps is not None:
            for mcp in self.mcps:
                self._tools.append({
                    "type": "mcp",
                    "server_label": mcp.server_label,
                    "server_url": mcp.server_url,
                    "require_approval": mcp.require_approval,
                    "headers": mcp.headers,
                    "allowed_tools": mcp.allowed_tools,
                })

        # File search currently allows a maximum of two vector stores
        if allow_file_search and self.vector_store_ids is not None:
            self._tools.append({
                "type": "file_search",
                "vector_store_ids": self.vector_store_ids
            })

        # If a welcome message is provided, add it to the chat history
        if self.welcome_message is not None:
            self._input.append({"role": "assistant", "content": self.welcome_message})
            self.add_section(
                "assistant",
                blocks=[self.create_block("text", self.welcome_message)]
            )

        # If files are uploaded statically, create tracked files for them
        if self.uploaded_files is not None:
            for uploaded_file in self.uploaded_files:
                shutil.copy(uploaded_file, self._temp_dir.name)
                self.track(os.path.join(self._temp_dir.name, os.path.basename(uploaded_file)))
                self._static_files.append(self._tracked_files[-1])

    @property
    def last_section(self) -> Optional["Section"]:
        """Returns the last section of the chat."""
        return self._sections[-1] if self._sections else None

    def summarize(self) -> None:
        """Update the chat summary."""
        sections = []
        for section in self._sections:
            if section.empty:
                continue
            s = {"role": section.role, "blocks": []}
            for block in section.blocks:
                if block.category in ["text", "code", "reasoning"]:
                    content = block.content
                else:
                    content = "Bytes"
                s["blocks"].append({
                    "category": block.category,
                    "content": content,
                    "filename": block.filename,
                    "file_id": block.file_id
                })
            sections.append(s)
        if sections:
            result = self._client.chat.completions.create(
                model="gpt-4o",
                temperature=0.001,
                messages=[
                    {"role": "developer", "content": SUMMARY_INSTRUCTIONS},
                    {"role": "user", "content": json.dumps(sections, indent=4)}
                ]
            )
            self.summary = result.choices[0].message.content

    def save(self, file_path: str) -> None:
        """Saves the chat history to a ZIP file."""
        if not file_path.endswith(".zip"):
            raise ValueError("File path must end with .zip")
        with tempfile.TemporaryDirectory() as t:
            sections = []
            for section in self._sections:
                s = {"role": section.role, "blocks": []}
                for block in section.blocks:
                    if block.category in ["text", "code", "reasoning"]:
                        content = block.content
                    else:
                        with open(f"{t}/{block.file_id}-{block.filename}", "wb") as f:
                            f.write(block.content)
                        content = "Bytes"
                    s["blocks"].append({
                        "category": block.category,
                        "content": content,
                        "filename": block.filename,
                        "file_id": block.file_id
                    })
                sections.append(s)
            for static_file in self._static_files:
                shutil.copy(static_file._file_path, t)
            data = {
                "model": self.model,
                "instructions": self.instructions,
                "temperature": self.temperature,
                "accept_file": self.accept_file,
                "uploaded_files": self.uploaded_files,
                "user_avatar": self.user_avatar,
                "assistant_avatar": self.assistant_avatar,
                "placeholder": self.placeholder,
                "welcome_message": self.welcome_message,
                "example_messages": self.example_messages,
                "info_message": self.info_message,
                "vector_store_ids": self.vector_store_ids,
                "allow_code_interpreter": self.allow_code_interpreter,
                "allow_file_search": self.allow_file_search,
                "allow_web_search": self.allow_web_search,
                "allow_image_generation": self.allow_image_generation,
                "sections": sections,
            }
            with open(f"{t}/data.json", "w") as f:
                json.dump(data, f, indent=4)
            with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as f:
                for root, dirs, files in os.walk(t):
                    for file in files:
                        f.write(
                            os.path.join(root, file),
                            arcname=os.path.join(os.path.basename(file_path.replace(".zip", "")), file)
                        )

    @classmethod
    def load(cls, history) -> "Chat":
        """Loads a chat history from a ZIP file."""
        if not history.endswith(".zip"):
            raise ValueError("History file must end with .zip")
        with tempfile.TemporaryDirectory() as t:
            with zipfile.ZipFile(history, "r") as f:
                f.extractall(t)
            dir_path = f"{t}/{history.replace('.zip', '')}" 
            with open(f"{dir_path}/data.json", "r") as f:
                data = json.load(f)
            chat = cls(
                model=data["model"],
                instructions=data["instructions"],
                temperature=data["temperature"],
                accept_file=data["accept_file"],
                uploaded_files=None if data["uploaded_files"] is None else [f"{dir_path}/{os.path.basename(x)}" for x in data["uploaded_files"]],
                user_avatar=data["user_avatar"],
                assistant_avatar=data["assistant_avatar"],
                placeholder=data["placeholder"],
                example_messages=data["example_messages"],
                info_message=data["info_message"],
                vector_store_ids=data["vector_store_ids"],
                allow_code_interpreter=data["allow_code_interpreter"],
                allow_file_search=data["allow_file_search"],
                allow_web_search=data["allow_web_search"],
                allow_image_generation=data["allow_image_generation"],
            )
            for section in data["sections"]:
                chat.add_section(section["role"], blocks=[])
                for block in section["blocks"]:
                    if block["category"] in ["text", "code", "reasoning"]:
                        chat._input.append({
                            "role": section["role"],
                            "content": block["content"]
                        })
                        chat._sections[-1].blocks.append(chat.create_block(
                            block["category"], block["content"]
                        ))
                    else:
                        uploaded_file = f"{dir_path}/{block['file_id']}-{block['filename']}"
                        with open(uploaded_file, "rb") as f:
                            content = f.read()
                        chat.track(uploaded_file)
                        chat._sections[-1].blocks.append(chat.create_block(
                            block["category"],
                            content,
                            filename=block["filename"],
                            file_id=block["file_id"]
                        ))
            chat._input.append({"role": "developer", "content": CHAT_HISTORY_INSTRUCTIONS})
        return chat

    def respond(self, prompt) -> None:
        """Sends the user prompt to the assistant and streams the response."""
        self._input.append({"role": "user", "content": prompt})
        self.add_section("assistant")
        events1 = self._client.responses.create(
            model=self.model,
            input=self._input,
            instructions=DEVELOPER_MESSAGE+self.instructions,
            temperature=self.temperature,
            tools=self._tools,
            previous_response_id=self._previous_response_id,
            stream=True,
            reasoning={"summary": "auto"},
        )
        self._input = []
        tool_calls = {}
        for event1 in events1:
            if event1.type == "response.completed":
                self._previous_response_id = event1.response.id
                self.input_tokens += event1.response.usage.input_tokens
                self.output_tokens += event1.response.usage.output_tokens
            elif event1.type == "response.output_text.delta":
                self.last_section.update_and_stream("text", event1.delta)
                self.last_section.last_block.content = re.sub(r"!?\[([^\]]+)\]\(sandbox:/mnt/data/([^\)]+)\)", r"\1 (`\2`)", self.last_section.last_block.content)
            elif event1.type == "response.code_interpreter_call_code.delta":
                self.last_section.update_and_stream("code", event1.delta)
            elif event1.type == "response.output_item.done" and event1.item.type == "function_call":   
                tool_calls[event1.item.name] = event1
            elif event1.type == "response.reasoning_summary_text.delta":
                self.last_section.update_and_stream("reasoning", event1.delta)
            elif event1.type == "response.reasoning_summary_text.done":
                self.last_section.last_block.content += "\n\n"
            elif event1.type == "response.image_generation_call.partial_image":
                self.last_section.update_and_stream(
                    "generated_image",
                    base64.b64decode(event1.partial_image_b64),
                    filename=f"{event1.item_id}.{event1.output_format}",
                    file_id=event1.item_id
                )
            elif event1.type == "response.output_text.annotation.added":
                if event1.annotation["type"] == "file_citation":
                    pass
                elif event1.annotation["type"] == "container_file_citation":                
                    if event1.annotation["file_id"] in event1.annotation["filename"]:
                        if Path(event1.annotation["filename"]).suffix in [".png", ".jpg", ".jpeg"]:
                            image_content = self._client.containers.files.content.retrieve(
                                file_id=event1.annotation["file_id"],
                                container_id=self._container_id
                            )
                            self.last_section.update_and_stream(
                                "image",
                                image_content.read(),
                                filename=event1.annotation["filename"],
                                file_id=event1.annotation["file_id"]
                            )
                    else:
                        cfile_content = self._client.containers.files.content.retrieve(
                            file_id=event1.annotation["file_id"],
                            container_id=self._container_id
                        )
                        self.last_section.update_and_stream(
                            "download",
                            cfile_content.read(),
                            filename=event1.annotation["filename"],
                            file_id=event1.annotation["file_id"]
                        )
        if tool_calls:
            for tool in tool_calls:
                function = [x for x in self.functions if x.name == tool][0]
                result = function.handler(**json.loads(tool_calls[tool].item.arguments))
                self._input.append({
                    "type": "function_call_output",
                    "call_id": tool_calls[tool].item.call_id,
                    "output": str(result)
                })
            events2 = self._client.responses.create(
                model=self.model,
                input=self._input,
                instructions=DEVELOPER_MESSAGE+self.instructions,
                temperature=self.temperature,
                tools=self._tools,
                previous_response_id=self._previous_response_id,
                stream=True,
            )
            self._input = []
            for event2 in events2:
                if event2.type == "response.completed":
                    self._previous_response_id = event2.response.id
                elif event2.type == "response.output_text.delta":
                    self.last_section.update_and_stream("text", event2.delta)

    def run(self, uploaded_files=None) -> None:
        """Runs the main assistant loop."""
        if self.allow_code_interpreter:
            result = self._client.containers.retrieve(container_id=self._container_id)
            if result.status == "expired":
                container = self._client.containers.create(name="streamlit-openai")
                self._container_id = container.id
                for tracked_file in self._tracked_files:
                    if tracked_file._is_container_file:
                        self._client.containers.files.create(
                            container_id=self._container_id,
                            file_id=tracked_file._openai_file.id,
                        )
            for tool in self._tools:
                if tool["type"] == "code_interpreter":
                    tool["container"] = self._container_id
        if self.info_message is not None:
            st.info(self.info_message)
        for section in self._sections:
            section.write()
        chat_input = st.chat_input(placeholder=self.placeholder, accept_file=self.accept_file)
        if chat_input is not None:
            if self.accept_file in [True, "multiple"]:
                prompt = chat_input.text
                attachments = chat_input.files
                if attachments:
                    if uploaded_files is None:
                        uploaded_files = attachments
                    else:
                        uploaded_files.extend(attachments)
            else:
                prompt = chat_input
                attachments = []
            section = self.create_section("user")
            with st.chat_message("user"):
                if attachments:
                    for attachment in attachments:
                        st.markdown(f":material/attach_file: `{attachment.name}`")
                        section.update(
                            "upload",
                            attachment.getvalue(),
                            filename=attachment.name,
                            file_id=attachment.file_id
                        )
                st.markdown(prompt)
                section.update("text", prompt)
            self._sections.append(section)
            self.handle_files(uploaded_files)
            self.respond(prompt)
        else:
            if self.example_messages is not None and not any(section.role == "user" for section in self._sections):
                if self._selected_example is None:
                    selected_example = st.pills(
                        "Examples",
                        options=self.example_messages,
                        label_visibility="collapsed"
                    )
                    if selected_example:
                        self._selected_example = selected_example
                        st.rerun()
                else:
                    with st.chat_message("user"):
                            st.markdown(self._selected_example)
                    self.add_section(
                        "user",
                        blocks=[self.create_block("text", self._selected_example)]
                    )
                    self.respond(self._selected_example)
        if self.summary == "New Chat":
            self.summarize()

    def handle_files(self, uploaded_files) -> None:
        """Handles uploaded files."""
        if uploaded_files is None:
            return
        else:
            for uploaded_file in uploaded_files:
                if uploaded_file.file_id in [x.uploaded_file.file_id for x in self._tracked_files if isinstance(x, UploadedFile)]:
                    continue
                self.track(uploaded_file)

    class TrackedFile():
        """A file that is tracked by the chat."""
        def __init__(
            self,
            chat: "Chat",
            uploaded_file: Optional[Union[UploadedFile, str]]
        ) -> None:
            """
            Initializes a TrackedFile instance.
            
            Args:
                chat (Chat): The parent Chat object.
                uploaded_file (UploadedFile or str): An UploadedFile object or a string representing the file path.
            """
            self.chat = chat
            self.uploaded_file = uploaded_file
            self._file_path = None
            self._openai_file = None
            self._vision_file = None
            self._skip_file_search = False
            self._is_container_file = False

            if isinstance(self.uploaded_file, str):
                self._file_path = Path(self.uploaded_file).resolve()
            elif isinstance(self.uploaded_file, UploadedFile):
                self._file_path = Path(os.path.join(self.chat._temp_dir.name, self.uploaded_file.name))
                with open(self._file_path, "wb") as f:
                    f.write(self.uploaded_file.getvalue())
            else:
                raise ValueError("uploaded_file must be an instance of UploadedFile or a string representing the file path.")

            self.chat._input.append(
                {"role": "user", "content": [{"type": "input_text", "text": f"File locally available at: {self._file_path}"}]}
            )

            if self._file_path.suffix == ".pdf":
                if self._openai_file is None:
                    with open(self._file_path, "rb") as f:
                        self._openai_file = self.chat._client.files.create(file=f, purpose="user_data")
                try:
                    # Test if the PDF file can be processed
                    response = self.chat._client.responses.create(
                        model=self.chat.model,
                        input=[{
                            "role": "user",
                            "content": [{"type": "input_file", "file_id": self._openai_file.id
                        }]}]
                    )
                    self.chat._input.append({
                        "role": "user",
                        "content": [{"type": "input_file", "file_id": self._openai_file.id}]
                    })
                    self._skip_file_search = True
                except Exception as e:
                    pass

            if self._file_path.suffix in VISION_EXTENSIONS:
                self._vision_file = self.chat._client.files.create(file=self._file_path, purpose="vision")
                self.chat._input.append({
                    "role": "user",
                    "content": [{"type": "input_image", "file_id": self._vision_file.id}]
                })

            if self.chat.allow_code_interpreter and self._file_path.suffix in CODE_INTERPRETER_EXTENSIONS:
                # If an image file is uploaded for vision purposes but is also 
                # supported by the code interpreter, it will be automatically 
                # uploaded to the code interpreter container.
                if self._file_path.suffix in VISION_EXTENSIONS:
                    self._openai_file = self._vision_file
                if self._openai_file is None:
                    with open(self._file_path, "rb") as f:
                        self._openai_file = self.chat._client.files.create(file=f, purpose="user_data")
                self.chat._client.containers.files.create(
                    container_id=self.chat._container_id,
                    file_id=self._openai_file.id,
                )
                self._is_container_file = True

            if self.chat.allow_file_search and not self._skip_file_search and self._file_path.suffix in FILE_SEARCH_EXTENSIONS:
                if self._openai_file is None:
                    with open(self._file_path, "rb") as f:
                        self._openai_file = self.chat._client.files.create(file=f, purpose="user_data")
                if self.chat._dynamic_vector_store is None:
                    self.chat._dynamic_vector_store = self.chat._client.vector_stores.create(
                        name="streamlit-openai"
                    )
                self.chat._client.vector_stores.files.create(
                    vector_store_id=self.chat._dynamic_vector_store.id,
                    file_id=self._openai_file.id
                )
                result = self.chat._client.vector_stores.retrieve(
                    vector_store_id=self.chat._dynamic_vector_store.id,
                )
                while result.status != "completed":
                    time.sleep(1)
                    result = self.chat._client.vector_stores.retrieve(
                        vector_store_id=self.chat._dynamic_vector_store.id,
                    )
                for tool in self.chat._tools:
                    if tool["type"] == "file_search":
                        if self.chat._dynamic_vector_store.id not in tool["vector_store_ids"]:
                            tool["vector_store_ids"].append(self.chat._dynamic_vector_store.id)
                        break
                else:
                    self.chat._tools.append({
                        "type": "file_search",
                        "vector_store_ids": [self.chat._dynamic_vector_store.id]
                    })

        def __repr__(self) -> None:
            return f"TrackedFile(uploaded_file='{self._file_path.name}')"
        
    def track(self, uploaded_file) -> None:
        """Tracks a file uploaded by the user."""
        self._tracked_files.append(
            self.TrackedFile(self, uploaded_file)
        )

    class Block():
        """A block of content in the chat."""
        def __init__(
            self,
            chat: "Chat",
            category: str,
            content: Optional[Union[str, bytes, openai.File]] = None,
            filename: Optional[str] = None,
            file_id: Optional[str] = None,
        ) -> None:
            """
            Initializes a Block instance.
            
            Args:
                chat (Chat): The parent Chat object.
                category (str): The type of content ('text', 'code', 'image', 'generated_image', 'download', 'upload').
                content (str or bytes): The content of the block.
                filename (str): The name of the file if the content is bytes.
                file_id (str): The ID of the file if the content is bytes.
            """
            self.chat = chat
            self.category = category
            self.content = content
            self.filename = filename
            self.file_id = file_id

            if self.content is None:
                self.content = ""
            else:
                self.content = content

        def __repr__(self) -> None:
            """Returns a string representation of the Block."""
            if self.category in ["text", "code", "reasoning"]:
                content = self.content
                if len(content) > 30:
                    content = content[:30].strip() + "..."
                content = repr(content)
            elif self.category in ["image", "generated_image", "download", "upload"]:
                content = "Bytes"
            return f"Block(category='{self.category}', content={content}, filename='{self.filename}', file_id='{self.file_id}')"

        def iscategory(self, category) -> bool:
            """Checks if the block belongs to the specified category."""
            return self.category == category

        def write(self) -> None:
            """Renders the block's content to the chat."""
            if self.category == "text":
                st.markdown(self.content)
            elif self.category == "code":
                with st.expander("", expanded=False, icon=":material/code:"):
                    st.code(self.content)
            elif self.category == "reasoning":
                with st.expander("", expanded=False, icon=":material/lightbulb:"):
                    st.markdown(self.content)
            elif self.category in ["image", "generated_image"]:
                st.image(self.content)
            elif self.category == "download":
                _, file_extension = os.path.splitext(self.filename)
                st.download_button(
                    label=self.filename,
                    data=self.content,
                    file_name=self.filename,
                    mime=MIME_TYPES[file_extension.lstrip(".")],
                    icon=":material/download:",
                    key=self.chat._download_button_key,
                )
                self.chat._download_button_key += 1
            elif self.category == "upload":
                st.markdown(f":material/attach_file: `{self.filename}`")

    def create_block(self, category, content=None, filename=None, file_id=None) -> "Block":
        """Creates a new Block object."""
        return self.Block(
            self, category, content=content, filename=filename, file_id=file_id
        )

    class Section():
        """A section of the chat."""
        def __init__(
            self,
            chat: "Chat",
            role: str,
            blocks: Optional[List["Block"]] = None,
        ) -> None:
            """
            Initializes a Section instance.
            
            Attributes:
                chat (Chat): The parent Chat object.
                role (str): The role associated with this message (e.g., "user" or "assistant").
                blocks (list): A list of Block instances representing message segments.
            """
            self.chat = chat
            self.role = role
            self.blocks = blocks
            self.delta_generator = st.empty()
            
        def __repr__(self) -> None:
            """Returns a string representation of the Section."""
            return f"Section(role='{self.role}', blocks={self.blocks})"

        @property
        def empty(self) -> bool:
            """Returns True if the section has no blocks."""
            return self.blocks is None

        @property
        def last_block(self) -> Optional["Block"]:
            """Returns the last block in the section or None if empty."""
            return None if self.empty else self.blocks[-1]

        def update(self, category, content, filename=None, file_id=None) -> None:
            """Updates the section with new content, appending or extending existing blocks."""
            if self.empty:
                self.blocks = [self.chat.create_block(
                    category, content, filename=filename, file_id=file_id
                )]
            elif category in ["text", "code", "reasoning"] and self.last_block.iscategory(category):
                self.last_block.content += content
            elif category == "generated_image" and self.last_block.iscategory(category):
                self.last_block.content = content
            else:
                self.blocks.append(self.chat.create_block(
                    category, content, filename=filename, file_id=file_id
                ))

        def write(self) -> None:
            """Renders the section's content in the Streamlit chat interface."""
            if self.empty:
                pass
            else:
                with st.chat_message(self.role, avatar=self.chat.user_avatar if self.role == "user" else self.chat.assistant_avatar):
                    for block in self.blocks:
                        block.write()

        def update_and_stream(self, category, content, filename=None, file_id=None) -> None:
            """Updates the section and streams the update live to the UI."""
            self.update(category, content, filename=filename, file_id=file_id)
            self.stream()

        def stream(self) -> None:
            """Renders the section content using Streamlit's delta generator."""
            with self.delta_generator:
                self.write()

    def create_section(self, role, blocks=None) -> "Section":
        """Creates a new Section object."""
        return self.Section(self, role, blocks=blocks)

    def add_section(self, role, blocks=None) -> None:
        """Adds a new Section."""
        self._sections.append(
            self.Section(self, role, blocks=blocks)
        )