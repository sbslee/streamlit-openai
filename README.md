[![PyPI version](https://badge.fury.io/py/streamlit-openai.svg)](https://badge.fury.io/py/streamlit-openai)

Welcome to the `streamlit-openai` package!

This package provides a Streamlit component for building interactive chat 
interfaces powered by OpenAI.

Here’s a quick overview of the package’s key features:

- Easily create chat interfaces in Streamlit
- Real-time streaming responses using the Responses API
- Integration with OpenAI tools: reasoning, function calling, remote MCP, file search, code interpreter, vision, image generation, web search, and more
- File input support for richer interactions
- Fully customizable chat interface, including model selection, temperature settings, and more
- Support for saving and retrieving chat history

# Table of Contents
- [Installation](#installation)
- [Usage](#usage)
- [Schematic Diagram](#schematic-diagram)
- [Features](#features)
  - [Function Calling](#function-calling)
    - [Image Generation Example](#image-generation-example)
    - [Web Search Example](#web-search-example)
    - [Audio Transcription Example](#audio-transcription-example)
  - [Reasoning](#reasoning)
  - [Remote MCP](#remote-mcp)
  - [File Inputs](#file-inputs)
    - [Message Attachments](#message-attachments)
    - [Static File Upload](#static-file-upload)
    - [File Uploader Widget](#file-uploader-widget)
  - [Vision](#vision)
  - [Image Generation](#image-generation)
  - [File Search](#file-search)
    - [PDF Vision Support](#pdf-vision-support)
    - [Vector Store Retrieval](#vector-store-retrieval)
  - [Web Search](#web-search)
  - [Code Interpreter](#code-interpreter)
  - [Chat History](#chat-history)
  - [Chat Summary](#chat-summary)
  - [Token Usage](#token-usage)
  - [Storage Management](#storage-management)
- [Customization](#customization)
  - [Model Selection](#model-selection)
  - [Temperature](#temperature)
  - [Instructions](#instructions)
  - [Avatar Image](#avatar-image)
  - [Welcome Message](#welcome-message)
  - [Example Messages](#example-messages)
  - [Info Message](#info-message)
  - [Input Box Placeholder](#input-box-placeholder)
- [Chat Completions and Assistants APIs](#chat-completions-and-assistants-apis)
- [Changelog](#changelog)

# Installation

```sh
$ pip install streamlit-openai streamlit openai
```

# Usage

Export your OpenAI API key:

```sh
$ export OPENAI_API_KEY='sk-...'
```

Save the following code to `app.py`:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat()

st.session_state.chat.run()
```

Run the app:

```sh
$ streamlit run app.py
```

# Schematic Diagram

The diagram below illustrates the `Section` and `Block` classes used
to create a chat interface.

In the diagram, the uploaded file (`instructions.txt`) contains the following 
content:

"Create a 2x10 table with random numbers and save it as a CSV file, using 'X' 
and 'Y' as column names. Then, generate a scatter plot based on this table. 
Save the plot as a PNG file. Finally, display both the plot and the table."

The assistant uses file search to retrieve the instructions from the uploaded 
file, and the code interpreter to execute the instructions and generate the 
output files.

![Schematic diagram](schematic_diagram.png)

# Features

## Function Calling

You can define and invoke custom functions within a chat using OpenAI's 
function calling capabilities. To create a custom function, provide the 
`name`, `description`, `parameters`, and `handler` arguments when initializing 
a `CustomFunction`.

### Image Generation Example

Update: As of the 0.1.2 release, the `streamlit_openai` package natively 
supports image generation (see [Image Generation](#image-generation)) 
Therefore, creating a custom function for this purpose is no longer necessary. 
However, if you prefer to define a custom image generation function, you can 
still do so using the `CustomFunction` class.

Below is an example of a custom function that generates an image based on a 
user-provided prompt:

```python
import streamlit as st
import openai
import streamlit_openai

if "chat" not in st.session_state:
    def handler(prompt):
        client = openai.OpenAI()
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return response.data[0].url
    
    generate_image = streamlit_openai.CustomFunction(
        name="generate_image",
        description="Generate an image based on a given prompt.",
        parameters={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "A description of the image to be generated.",
                }
            },
            "required": ["prompt"]
        },
        handler=handler
    )

    st.session_state.chat = streamlit_openai.Chat(
        functions=[generate_image]
    )

st.session_state.chat.run()
```

### Web Search Example

Update: As of the 0.1.2 release, the `streamlit_openai` package natively 
supports web search (see [Web Search](#web-search)). Therefore, creating a 
custom function for this purpose is no longer necessary. However, if you 
prefer to define a custom web search function, you can still do so using the 
`CustomFunction` class.

You can create a custom function to search the web using a given query. Below 
is an example:

```python
import streamlit as st
import openai
import streamlit_openai

if "chat" not in st.session_state:
    def handler(prompt):
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-search-preview",
            web_search_options={},
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    
    search_web = streamlit_openai.CustomFunction(
        name="search_web",
        description="Search the web using a query.",
        parameters={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Search query.",
                }
            },
            "required": ["prompt"]
        },
        handler=handler
    )

    st.session_state.chat = streamlit_openai.Chat(
        functions=[search_web],
    )

st.session_state.chat.run()
```

### Audio Transcription Example

You can create a custom function to transcribe audio files. Below is an 
example:

```python
import streamlit as st
import openai
import streamlit_openai

if "chat" not in st.session_state:
    def handler(audio_file):
        client = openai.OpenAI()
        response = client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=open(audio_file, "rb"),
        )
        return response.text
    
    transcribe_audio = streamlit_openai.CustomFunction(
        name="transcribe_audio",
        description="Convert speech to text.",
        parameters={
            "type": "object",
            "properties": {
                "audio_file": {
                    "type": "string",
                    "description": "The audio file to transcribe.",
                }
            },
            "required": ["audio_file"]
        },
        handler=handler
    )

    st.session_state.chat = streamlit_openai.Chat(
        functions=[transcribe_audio],
    )
    
st.session_state.chat.run()
```

## Reasoning

The `Chat` class supports OpenAI's reasoning capabilities, allowing the
assistant to perform complex reasoning tasks. To enable reasoning, select a 
reasoning model when initializing the `Chat` class (e.g., `model="o3"`). 
Depending on the selected model, you may need to disable some features that 
are not compatible with reasoning. For example, web search is not supported 
with reasoning models, so you should set `allow_web_search=False` when 
initializing the `Chat` class.

Example:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat(
        model="o3",             # Select a reasoning model
        allow_web_search=False, # Disable web search
    )

st.session_state.chat.run()
```

## Remote MCP

The `Chat` class supports OpenAI's remote MCP (Model Context Protocol) for 
performing various tasks. To create a remote MCP, provide the required 
parameters -- `server_label` and `server_url` -- when initializing a 
`RemoteMCP`. Depending on your use case, you may also need to specify 
additional parameters such as `require_approval`, `headers`, and 
`allowed_tools`.

Example:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    deepwiki = streamlit_openai.RemoteMCP(
        server_label="deepwiki",
        server_url="https://mcp.deepwiki.com/mcp",
    )

    st.session_state.chat = streamlit_openai.Chat(
        mcps=[deepwiki]
    )

st.session_state.chat.run()
```

## File Inputs

You can provide file inputs to the chat interface, allowing the assistant
to access and utilize the content of the files during the conversation.

### Message Attachments

You can upload files in the chat by clicking the attachment icon or dragging 
them into the input box. Uploaded files are sent along with your message, and 
the assistant can access their content. This behavior is controlled by the 
`accept_file` parameter when initializing the `Chat` class. Below is an 
example of how to enable file uploads in the chat interface:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat(
        accept_file="multiple" # Allow multiple file uploads (default)
        # accept_file=True,    # Allow only one file upload
        # accept_file=False,   # Disable file uploads entirely
    )

st.session_state.chat.run()
```

### Static File Upload

You can upload files statically by providing the `uploaded_files` parameter
when initializing the `Chat` class. Example:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat(
        uploaded_files=["example.pdf"]
    )

st.session_state.chat.run()
```

### File Uploader Widget

You can use `st.file_uploader` to allow users to upload files dynamically. 
Note that while the widget supports file removal, the files will still remain 
in the chat context. Example:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat()
    
uploaded_files = st.sidebar.file_uploader("Upload Files", accept_multiple_files=True)

st.session_state.chat.run(uploaded_files=uploaded_files)
```

## Vision

The `Chat` class supports OpenAI’s vision capabilities, allowing image input 
to be processed within a chat.

Currently, the following image formats are supported: `.png`, `.jpeg`, `.jpg`, 
`.webp`, and `.gif`.

Here’s an example:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat(
        uploaded_files=["example.jpeg"]
    )

st.session_state.chat.run()
```

## Image Generation

The `Chat` class supports OpenAI's image generation capabilities, allowing the
assistant to generate images based on user prompts. By default, this feature is
enabled, but you can disable it by setting `allow_image_generation=False` when
initializing the `Chat` class. Example:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat(
        allow_image_generation=True,    # Enable image generation (default)
        # allow_image_generation=False, # Disable it
    )

st.session_state.chat.run()
```

## File Search

The `Chat` class supports file search capabilities, enabling the assistant to 
search through uploaded files and retrieve relevant information during a 
conversation. To disable it, set `allow_file_search=False` when initializing 
`Chat`.

The following file formats are currently supported: `.c`, `.cpp`, `.cs`, 
`.css`, `.doc`, `.docx`, `.go`, `.html`, `.java`, `.js`, `.json`, `.md`, 
`.pdf`, `.php`, `.pptx`, `.py`, `.rb`, `.sh`, `.tex`, `.ts`, and `.txt`.

It's notewordthy that the file search feature doesn't support image 
processing, except for PDFs, which can be processed using OpenAI's vision. 
See [PDF Vision Support](#pdf-vision-support) for more details.

When the user uploads one or more files, a new vector store is created, and 
the files are indexed for search. If additional files are uploaded later, the 
existing vector store is updated with the new files.

Note that OpenAI's file search currently supports a maximum of two vector 
stores in use simultaneously. See 
[Vector Store Retrieval](#vector-store-retrieval) for more details.

Below is an example:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat(
        allow_file_search=True,   # Enable file search (default)
        # allow_file_search=False # Disable it
        uploaded_files=["example.docx"]
    )

st.session_state.chat.run()
```

### PDF Vision Support

File search retrieves information from a knowledge base using semantic and 
keyword search. However, it does not support processing images within files 
-- except in the case of PDFs. PDF files can be processed using OpenAI's 
vision capabilities, allowing the assistant to extract both text and images 
from each page. Notably, PDFs processed this way do not trigger the creation 
of a vector store, as they are handled through the vision model instead.

There is a limitation, however: you can upload up to 100 pages and a total of 
32MB of content in a single PDF upload. If the uploaded PDF exceeds this 
limit, the assistant will fall back to standard file search, which indexes 
only the text content of the PDF.

### Vector Store Retrieval

If you already have existing vector stores created using the OpenAI API, you 
can use them in the chat interface. This is particularly useful for retrieving 
relevant information from previously indexed files without needing to 
re-upload them -- especially if the files are large or numerous.

To use existing vector stores in a chat, provide their IDs when initializing 
the `Chat` class. This enables the system to search and retrieve relevant 
information from those stores.

Note that OpenAI's file search currently supports a maximum of two vector 
stores at a time, meaning you can provide up to two vector store IDs. However, 
if you specify two vector store IDs, you won’t be able to upload new files. 
This is by design -- existing vector stores are not updated because they are 
presumably important and shared across applications, and modifying them could 
lead to unintended issues.

Example:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat(
        vector_store_ids=["vs_...", "vs_..."]
    )
st.session_state.chat.run()
```

## Web Search

By default, the `Chat` class supports OpenAI's web search capability,
allowing the assistant to retrieve up-to-date information from the web.
To disable this feature, set `allow_web_search=False` when initializing
the `Chat` class. Example:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat(
        allow_web_search=True    # Enable web search (default)
        # allow_web_search=False # Disable it
    )

st.session_state.chat.run()
```

## Code Interpreter

By default, the `Chat` class runs Python code in a sandboxed environment using 
OpenAI's code interpreter. It can read, write, and analyze files in formats 
like text, CSV, and images. To disable this, set 
`allow_code_interpreter=False` when initializing `Chat`.

The following file formats are currently supported: `.c`, `.cs`, `.cpp`, 
`.csv`, `.doc`, `.docx`, `.html`, `.java`, `.json`, `.md`, `.pdf`, `.php`, 
`.pptx`, `.py`, `.rb`, `.tex`, `.txt`, `.css`, `.js`, `.sh`, `.ts`, `.csv`, 
`.jpeg`, `.jpg`, `.gif`, `.pkl`, `.png`, `.tar`, `.xlsx`, `.xml`, and `.zip`.

Example:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat(
        allow_code_interpreter=True    # Enable code interpreter (default)
        # allow_code_interpreter=False # Disable it
    )

st.session_state.chat.run()
```

## Chat History

You can save chat history to let users resume conversations across sessions. 
Use the `Chat` class’s `save` method to save history as a ZIP file. Example:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat()
    
with st.sidebar:
    if st.button("Save"):
        st.session_state.chat.save("history.zip")

st.session_state.chat.run()
```

After saving the chat history, you can load it in a new session by passing
the file path to the `Chat.load` method:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat.load("history.zip")

st.session_state.chat.run()
```

## Chat Summary

The `Chat` class automatically generates a summary of the chat history, 
accessible via the `Chat.summary` property. This summary is created using 
OpenAI's Chat Completions API and provides a concise overview of the 
conversation. Note that when a new chat is started, the default summary is 
`"New Chat"`. When there is enough context in the chat history, the summary 
will be automatically generated. Once the summary is generated, it will not 
change.

## Token Usage

The `Chat` class offers the `Chat.input_tokens` and `Chat.output_tokens` 
properties to monitor token usage during a chat session. These properties 
return the number of input and output tokens used, respectively. This feature 
is particularly useful for tracking token consumption and managing costs when 
utilizing OpenAI's API.

## Storage Management

You can delete all vector stores, files, and containers associated with the 
exported API key using the command-line interface:

```sh
$ streamlit-openai -h
usage: streamlit-openai [-h] [-v] [--keep ID [ID ...]] {delete-all,delete-files,delete-vector-stores,delete-containers}

CLI tool to delete OpenAI files, vector stores, and containers.

positional arguments:
  {delete-all,delete-files,delete-vector-stores,delete-containers}
                        command to execute

options:
  -h, --help            show this help message and exit
  -v, --version         show the version of the tool
  --keep ID [ID ...]    list of IDs to keep (e.g., file-123, vs_456, cntr_789)
```

# Customization

## Model Selection

The default model used by the assistant in the chat interface is `gpt-4o`. You
can customize the model used by the assistant by providing the `model` 
parameter. Example:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat(model="o3-mini")

st.session_state.chat.run()
```

## Temperature

You can customize the temperature used by the assistant in the chat interface
by providing the `temperature` parameter. The temperature controls the 
randomness of the assistantant's responses. Example:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat(temperature=0.5)

st.session_state.chat.run()
```

## Instructions

You can customize the instructions provided to the assistant in the chat
interface by providing the `instructions` parameter. The instructions provide 
context for the assistant and can help guide its responses. Example:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat(
        instructions="You are a helpful assistant."
    )

st.session_state.chat.run()
```

## Avatar Image

You can customize the avatar images for the assistant and user in the chat 
interface by providing the `assistant_avatar` and `user_avatar` parameters. 
Example:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat(assistant_avatar="🦖")

st.session_state.chat.run()
```

## Welcome Message

You can customize the welcome message displayed in the chat interface by
providing the `welcome_message` parameter.

Note that if a chat history is provided, the welcom message will not be 
displayed, as the chat history takes precedence.

Example:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat(
        welcome_message="Hello! How can I assist you today?"
    )

st.session_state.chat.run()
```

## Example Messages

You can use the `example_messages` parameter to provide example messages in 
the chat interface, helping users understand how to interact with the 
assistant.

Note that if a chat history is provided, the example messages will not be 
displayed, as the chat history takes precedence.

Example:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat(
        example_messages=[
            "Can you tell me a joke?",
            "What is the capital of France?",
            "How do you make a paper airplane?",
            "What is the weather like today?",
        ],
    )

st.session_state.chat.run()
```

## Info Message

The `info_message` parameter displays a persistent message at the top of the 
chat, guiding users on how to interact with the assistant. Example:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat(
        info_message="Don't share sensitive info. AI may be inaccurate."
    )

st.session_state.chat.run()
```

## Input Box Placeholder

You can set custom placeholder text for the chat input box using the 
`placeholder` parameter when initializing the `Chat` class. Example:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat(
        placeholder="Type your message here..."
    )

st.session_state.chat.run()
```

# Chat Completions and Assistants APIs

Before the 0.1.0 release, the `streamlit-openai` package supported the OpenAI 
Chat Completions and Assistants APIs. However, the Responses API is now 
OpenAI's most advanced interface for generating model outputs, and the 
Assistants API is scheduled for deprecation in early 2026. While the Chat 
Completions API will remain available, OpenAI recommends using the Responses 
API for all new applications, as it offers a more powerful and flexible way 
to interact with their models. Starting with the 0.1.0 release, the package 
has been updated to use the Responses API exclusively.

# Changelog

For a detailed list of changes, please refer to the [CHANGELOG](CHANGELOG.md).