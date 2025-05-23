[![PyPI version](https://badge.fury.io/py/streamlit-openai.svg)](https://badge.fury.io/py/streamlit-openai)

Welcome to the `streamlit-openai` package!

This package provides a Streamlit component for building interactive chat 
interfaces powered by OpenAI's API. It supports both the Chat Completions and 
Assistants APIs, with built-in integration for OpenAI tools such as function 
calling, file search, and more.

Below is a quick overview of the package's key features:

- Easily create chat interfaces in Streamlit
- Support for OpenAI’s Chat Completions and Assistants APIs
- Real-time streaming responses
- Integration with OpenAI tools: Function Calling, File Search, and Code Interpreter
- File input support for richer interactions
- Fully customizable chat interface, including model selection, temperature, and more

# Table of Contents
- [Installation](#installation)
- [Usage](#usage)
- [Schematic Diagram](#schematic-diagram)
- [Chat Completions API](#chat-completions-api)
  - [Function Calling](#function-calling)
  - [File Inputs](#file-inputs)
- [Assistants API](#assistants-api)
  - [Function Calling](#function-calling-1)
  - [File Inputs](#file-inputs-1)
  - [File Search](#file-search)
  - [Code Interpreter](#code-interpreter)
  - [Existing Assistant Retrieval](#existing-assistant-retrieval)
- [Customization](#customization)
  - [Model Selection](#model-selection)
  - [Temperature](#temperature)
  - [Instructions](#instructions)
  - [Avatar Image](#avatar-image)
  - [Welcome Message](#welcome-message)
  - [Example Messages](#example-messages)
  - [Info Message](#info-message)
  - [Input Box Placeholder](#input-box-placeholder)
  - [Function Calling](#function-calling-2)
    - [Image Generation Example](#image-generation-example)
    - [Web Search Example](#web-search-example)
    - [Audio Transcription Example](#audio-transcription-example)

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
    # Use Chat Completions API
    st.session_state.chat = streamlit_openai.ChatCompletions()

    # Alternatively, use Assistants API
    # st.session_state.chat = streamlit_openai.Assistants()

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

# Chat Completions API

The `ChatCompletions` class is a wrapper around OpenAI’s Chat Completions API,
which allows you to create a chat interface with a single assistant. The
`ChatCompletions` class provides a simple interface for sending messages to
the assistant and receiving responses. It also supports OpenAI’s built-in
tools, such as file input and function calling.

## Function Calling

You can define and call custom functions within a chat using OpenAI’s function 
calling capabilities. To create a custom function, define a `CustomFunction` 
class that takes two input arguments: `definition` (a dictionary describing 
the function) and `function` (the actual callable method). Below is an example 
of a custom function that generates an image based on a given prompt:

```python
import streamlit as st
import openai
import streamlit_openai

if "chat" not in st.session_state:
    definition = {
        "name": "generate_image",
        "description": "Generate an image based on a given prompt.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "A description of the image to be generated.",
                }
            },
            "required": ["prompt"]
        }
    }

    def function(prompt):
        client = openai.OpenAI()
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return response.data[0].url
    
    generate_image = streamlit_openai.utils.CustomFunction(definition, function)

    st.session_state.chat = streamlit_openai.ChatCompletions(
        functions=[generate_image],
    )

st.session_state.chat.run()
```

## File Inputs

The `ChatCompletions` class allows you to upload files and use them as context 
for the assistant. 

Currently, the only natively supported file type is PDF. However, it is 
possible to upload other file types by providing a custom function to handle 
them.

One way to provide file inputs is to use the `message_files` parameter when
initializing the `ChatCompletions` class. Below is an example of how to
upload a PDF file and use it as context for the assistant:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.ChatCompletions(
        message_files=["example.pdf"]
    )

st.session_state.chat.run()
```

Alternatively, you can use the `st.file_uploader` method to allow users to
upload files dynamically. Below is an example of how to use the `st.file_uploader`
method to upload a PDF file and use it as context for the assistant:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.ChatCompletions()
    
uploaded_files = st.sidebar.file_uploader("Upload Files", accept_multiple_files=True)

st.session_state.chat.run(uploaded_files=uploaded_files)
```

# Assistants API

The `Assistants` class is a wrapper around OpenAI’s Assistants API, which 
allows you to create and manage assistants that can perform various tasks. The
`Assistants` class provides a simple interface for creating, updating, and
retrieving assistants, as well as managing their state and context.

## Function Calling

You can define and call custom functions within a chat using OpenAI’s function 
calling capabilities. To create a custom function, define a `CustomFunction` 
class that takes two input arguments: `definition` (a dictionary describing 
the function) and `function` (the actual callable method). Below is an example 
of a custom function that generates an image based on a given prompt:

```python
import streamlit as st
import openai
import streamlit_openai

if "chat" not in st.session_state:
    definition = {
        "name": "generate_image",
        "description": "Generate an image based on a given prompt.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "A description of the image to be generated.",
                }
            },
            "required": ["prompt"]
        }
    }

    def function(prompt):
        client = openai.OpenAI()
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return response.data[0].url
    
    generate_image = streamlit_openai.utils.CustomFunction(definition, function)

    st.session_state.chat = streamlit_openai.Assistants(
        functions=[generate_image],
    )

st.session_state.chat.run()
```

## File Inputs

The `Assistants` class allows you to upload files and use them as context 
for the assistant. When provding file inputs, you need to specify how the files
will be used by setting `file_search` and `code_interpreter` parameters when 
initializing the `Assistants` class.

Note that the `file_search` and `code_interpreter` features support different 
file types. Additionally, you can upload file types not natively supported by 
either feature by providing a custom function to handle them.

One way to provide file inputs is to use the `message_files` parameter when
initializing the `Assistants` class. Below is an example of how to
upload a PDF file and use it as context for the assistant:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Assistants(
        file_search=True,
        code_interpreter=True,
        message_files=["example.pdf"],
    )

st.session_state.chat.run()
```

Alternatively, you can use the `st.file_uploader` method to allow users to
upload files dynamically. Below is an example of how to use the `st.file_uploader`
method to upload a PDF file and use it as context for the assistant:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Assistants(
        file_search=True,
        code_interpreter=True,
    )
    
uploaded_files = st.sidebar.file_uploader("Upload Files", accept_multiple_files=True)

st.session_state.chat.run(uploaded_files=uploaded_files)
```

## File Search

You can allow models to search your files for relevant information before 
generating a response by using OpenAI’s file search capabilities. To enable 
file search, set the `file_search` parameter to `True` when initializing the 
`Assistants` class. Note that this feature is available only in the Assistants 
API and not in the Chat Completions API from OpenAI. Below is an example of
how to enable file search in a chat interface:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Assistants(file_search=True)
    
uploaded_files = st.sidebar.file_uploader("Upload Files", accept_multiple_files=True)

st.session_state.chat.run(uploaded_files=uploaded_files)
```

## Code Interpreter

You can allow models to run Python code in a sandboxed execution environment 
using OpenAI’s code interpreter capabilities. To enable code interpreter, set 
the `code_interpreter` parameter to `True` when initializing the `Assistants` 
class. Note that this feature is available only in the Assistants API and not 
in the Chat Completions API from OpenAI. Below is an example of how to enable 
code interpreter in a chat interface:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Assistants(code_interpreter=True)

st.session_state.chat.run()
```

## Existing Assistant Retrieval
You can retrieve an existing assistant by providing its ID when initializing
the `Assistants` class. This allows you to continue a conversation with an
existing assistant without losing context. Below is an example of how to
retrieve an existing assistant in a chat interface:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.Assistants(assistant_id="asst_...")
    
st.session_state.chat.run()
```

# Customization

## Model Selection
The default model used by the assistant in the chat interface is `gpt-4o`. You
can customize the model used by the assistant by providing the `model` parameter
when initializing the `ChatCompletions` or `Assistants` class. Below is an
example of how to customize the model in a chat interface:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.ChatCompletions(model="o3-mini")

st.session_state.chat.run()
```

## Temperature
You can customize the temperature used by the assistant in the chat interface
by providing the `temperature` parameter when initializing the `ChatCompletions`
or `Assistants` class. The temperature controls the randomness of the 
assistantant's responses. Below is an example of how to customize the 
temperature in a chat interface:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.ChatCompletions(temperature=0.5)

st.session_state.chat.run()
```

## Instructions
You can customize the instructions provided to the assistant in the chat
interface by providing the `instructions` parameter when initializing the
`ChatCompletions` or `Assistants` class. The instructions provide context
for the assistant and can help guide its responses. Below is an example of
how to customize the instructions in a chat interface:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.ChatCompletions(
        instructions="You are a helpful assistant."
    )

st.session_state.chat.run()
```

## Avatar Image
You can customize the avatar images for the assistant and user in the chat interface
by providing the `assistant_avatar` and `user_avatar` parameters when initializing
the `ChatCompletions` or `Assistants` class. Below is an example of how to
customize the avatar images in a chat interface:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.ChatCompletions(assistant_avatar="🦖")

st.session_state.chat.run()
```

## Welcome Message
You can customize the welcome message displayed in the chat interface by
providing the `welcome_message` parameter when initializing the `ChatCompletions`
or `Assistants` class. Below is an example of how to customize the welcome
message in a chat interface:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.ChatCompletions(
        welcome_message="Hello! How can I assist you today?"
    )

st.session_state.chat.run()
```

## Example Messages
You can use the `example_messages` parameter to provide example messages in 
the chat interface, helping users understand how to interact with the 
assistant. Below is an example of how to provide example messages in a chat 
interface:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.ChatCompletions(
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
The `info_message` parameter allows you to display an informational message 
within the chat interface, helping users grasp key details about how to 
interact effectively with the assistant. Here's an example of how to include 
such a message in the chat interface:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.ChatCompletions(
        info_message="This is an informative and helpful message.",
    )

st.session_state.chat.run()
```

## Input Box Placeholder
You can customize the placeholder text for the input box in the chat interface
by providing the `placeholder` parameter when initializing the `ChatCompletions`
or `Assistants` class. Below is an example of how to customize the placeholder
text in a chat interface:

```python
import streamlit as st
import streamlit_openai

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.ChatCompletions(
        placeholder="Type your message here..."
    )

st.session_state.chat.run()
```

## Function Calling
You can define and call custom functions within a chat using OpenAI’s function
calling capabilities. To create a custom function, define a `CustomFunction`
class that takes two input arguments: `definition` (a dictionary describing
the function) and `function` (the actual callable method).

### Image Generation Example
You can create a custom function to generate an image from a given prompt. 
Below is an example:

```python
import streamlit as st
import openai
import streamlit_openai

if "chat" not in st.session_state:
    definition = {
        "name": "generate_image",
        "description": "Generate an image based on a given prompt.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "A description of the image to be generated.",
                }
            },
            "required": ["prompt"]
        }
    }

    def function(prompt):
        client = openai.OpenAI()
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return response.data[0].url
    
    generate_image = streamlit_openai.utils.CustomFunction(definition, function)

    st.session_state.chat = streamlit_openai.Assistants(
        functions=[generate_image],
    )

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
    definition = {
        "name": "search_web",
        "description": "Searches the web using a query.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Search query.",
                }
            },
            "required": ["prompt"]
        }
    }

    def function(prompt):
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-search-preview",
            web_search_options={},
            messages=[{"role": "user", "content": prompt}],
        )

        return response.choices[0].message.content
    
    search_web = streamlit_openai.utils.CustomFunction(definition, function)

    st.session_state.chat = streamlit_openai.ChatCompletions(
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
    definition = {
        "name": "transcribe_audio",
        "description": "Convert speech to text.",
        "parameters": {
            "type": "object",
            "properties": {
                "audio_file": {
                    "type": "string",
                    "description": "The audio file to transcribe.",
                }
            },
            "required": ["audio_file"]
        }
    }

    def function(audio_file):
        client = openai.OpenAI()
        response = client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=open(audio_file, "rb"),
        )
        return response.text
    
    transcribe_audio = streamlit_openai.utils.CustomFunction(definition, function)

    st.session_state.chat = streamlit_openai.ChatCompletions(
        functions=[transcribe_audio],
    )

uploaded_files = st.sidebar.file_uploader("Upload Files", accept_multiple_files=True)

st.session_state.chat.run(uploaded_files=uploaded_files)
```