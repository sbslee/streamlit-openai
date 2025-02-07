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
    st.session_state.chat = so.utils.BasicChat()

st.session_state.chat.start()
```

Run the app:

```
$ streamlit run app.py
```