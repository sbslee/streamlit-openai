# streamlit-openai

## Installation

```sh
$ pip install streamlit-openai
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
    st.session_state.chat = streamlit_openai.utils.BasicChat()

    # Alternatively, use Assistants API
    # st.session_state.chat = streamlit_openai.utils.AssistantChat()

st.session_state.chat.start()
```

Run the app:

```sh
$ streamlit run app.py
```