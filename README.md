# streamlit-openai

## Installation

```
$ pip install streamlit-openai
```

## Usage

Save the following code to `app.py`:

```
import streamlit as st
import streamlit_openai as so

if "chat" not in st.session_state:
    # Use Chat Completions API
    st.session_state.chat = so.utils.BasicChat()

    # Alternatively, use Assistants API
    # st.session_state.chat = so.utils.AssistantChat()

st.session_state.chat.start()
```

Run the app:

```
$ streamlit run app.py
```