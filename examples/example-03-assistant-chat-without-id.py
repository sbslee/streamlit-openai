import streamlit as st
import streamlit_openai as so
from streamlit_openai.functions import GenerateImage

st.title("Example 3: Assistant Chat without ID")

if "submitted" not in st.session_state:
    st.session_state.submitted = False

if not st.session_state.submitted:
    with st.form("my_form"):
        st.session_state.openai_api_key = st.text_input("OpenAI API Key", type="password")
        st.session_state.submitted = st.form_submit_button("Submit")
else:
    if "chat" not in st.session_state:
        st.session_state.chat = so.utils.AssistantChat(
            openai_api_key=st.session_state.openai_api_key,
            functions=[GenerateImage],
        )
    st.session_state.chat.start()