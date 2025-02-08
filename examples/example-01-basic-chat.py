import streamlit as st
import streamlit_openai
from streamlit_openai.functions import GenerateImage

st.title("Example 1: Basic Chat")

if "submitted" not in st.session_state:
    st.session_state.submitted = False

if not st.session_state.submitted:
    with st.form("my_form"):
        st.session_state.openai_api_key = st.text_input("OpenAPI API Key", type="password")
        st.session_state.submitted = st.form_submit_button("Submit")
        if st.session_state.submitted:
            st.rerun()
else:
    if "chat" not in st.session_state:
        st.session_state.chat = streamlit_openai.utils.BasicChat(
            openai_api_key=st.session_state.openai_api_key,
            functions=[GenerateImage],
        )
    st.session_state.chat.start()