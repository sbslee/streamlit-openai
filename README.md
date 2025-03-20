# streamlit-openai

## Installation

```sh
$ pip install streamlit-openai streamlit openai
```

## Usage

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
    st.session_state.chat = streamlit_openai.utils.CompletionChat()

    # Alternatively, use Assistants API
    # st.session_state.chat = streamlit_openai.utils.AssistantChat()

st.session_state.chat.start()
```

Run the app:

```sh
$ streamlit run app.py
```

## Function calling

```python
import streamlit as st
import streamlit_openai

class GenerateImage:
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
        response = st.session_state.chat.client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return response.data[0].url

if "chat" not in st.session_state:
    st.session_state.chat = streamlit_openai.utils.CompletionChat(
        functions=[GenerateImage]
    )

st.session_state.chat.start()
```