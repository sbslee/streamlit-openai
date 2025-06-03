[![PyPI version](https://badge.fury.io/py/streamlit-openai.svg)](https://badge.fury.io/py/streamlit-openai)

Welcome to the `streamlit-openai` package!

This package provides a Streamlit component for building interactive chat 
interfaces powered by OpenAI.

Here’s a quick overview of the package’s key features:

- Easily create chat interfaces in Streamlit
- Real-time streaming responses using the Responses API
- Integration with OpenAI tools: function calling, file search, code interpreter, vision, and more
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
  - [File Inputs](#file-inputs)
    - [Message Attachments](#message-attachments)
    - [Static File Upload](#static-file-upload)
    - [File Uploader Widget](#file-uploader-widget)
  - [Vision](#vision)
  - [File Search](#file-search)
    - [Vector Store Retrieval](#vector-store-retrieval)
  - [Code Interpreter](#code-interpreter)
  - [Chat History](#chat-history)
- [Customization](#customization)
  - [Model Selection](#model-selection)
  - [Temperature](#temperature)
  - [Instructions](#instructions)
  - [Avatar Image](#avatar-image)
  - [Welcome Message](#welcome-message)
  - [Example Messages](#example-messages)
  - [Info Message](#info-message)
  - [Input Box Placeholder](#input-box-placeholder)

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

The following diagram illustrates the `Container` and `Block` classes used
to create a chat interface:

![Schematic diagram](schematic_diagram.png)

# Features

## Function Calling

You can define and invoke custom functions within a chat using OpenAI's 
function calling capabilities. To create a custom function, provide the 
`name`, `description`, `parameters`, and `handler` arguments when initializing 
a `CustomFunction`.

### Image Generation Example

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

    st.session_state.chat = streamlit_openai.Chat(functions=[generate_image])

st.session_state.chat.run()
```

### Web Search Example
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
    
    search_web = streamlit_openai.utils.CustomFunction(
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
    
    transcribe_audio = streamlit_openai.utils.CustomFunction(
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

uploaded_files = st.sidebar.file_uploader("Upload Files", accept_multiple_files=True)

st.session_state.chat.run(uploaded_files=uploaded_files)
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
when initializing the `Chat` class. This allows you to include files that
are always available in the chat interface. Below is an example of how to
upload a PDF file statically:

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

You can use `st.file_uploader` to let users upload files dynamically. While the 
widget allows file removal, the files remain in the chat history and context. 
Here's an example of how to use it:

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
to be processed within a chat. Currently, the following image formats are 
supported: `.png`, `.jpeg`, `.jpg`, `.webp`, and `.gif`. Here’s an example:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat(
        message_files=["example.jpeg"]
    )

st.session_state.chat.run()
```

## File Search

The `Chat` class supports file search capabilities, enabling the assistant to 
search through uploaded files and retrieve relevant information during a 
conversation. The following file formats are currently supported: `.c`, 
`.cpp`, `.cs`, `.css`, `.doc`, `.docx`, `.go`, `.html`, `.java`, `.js`, 
`.json`, `.md`, `.pdf`, `.php`, `.pptx`, `.py`, `.rb`, `.sh`, `.tex`, `.ts`, 
and `.txt`. Below is an example:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat(
        message_files=["example.pdf"]
    )

st.session_state.chat.run()
```

### Vector Store Retrieval

To use existing vector stores in a chat, provide their IDs when initializing 
the `Chat` class. This enables search and retrieval of relevant information. 
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

## Code Interpreter

By default, the `Chat` class enables models to run Python code in a sandboxed 
environment using OpenAI’s code interpreter. This supports tasks like data 
analysis and calculations. To disable it, set `allow_code_interpreter=False` 
when initializing `Chat`. Example:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Chat(allow_code_interpreter=True)

st.session_state.chat.run()
```

## Chat History

You can save chat history to let users resume conversations across sessions. 
Use the `Chat` class’s `save` method to save history as a ZIP file. Currently, 
only text is saved—other file types (e.g., images) are not supported. Example:

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

After saving the chat history, you can load it in a new session by passing the 
history parameter when initializing the `ChatCompletions` or `Assistants` 
class. Below is an example of how to load a chat history:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.ChatCompletions(history="history.zip")

st.session_state.chat.run()
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
providing the `welcome_message` parameter. Example:

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
assistant. Example:

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