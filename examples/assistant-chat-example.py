import streamlit as st
from streamlit_openai import AssistantChat

st.title("Assistant Chat Example")

if "submitted" not in st.session_state:
    st.session_state.submitted = False

if not st.session_state.submitted:
    with st.form("my_form"):
        st.session_state.openai_api_key = st.text_input("OpenAI API Key", type="password")
        st.session_state.assistant_id = st.text_input("OpenAI Assistant ID", type="password")
        st.session_state.submitted = st.form_submit_button("Submit")
else:
    if "chat" not in st.session_state:
        st.session_state.chat = AssistantChat(
            openai_api_key=st.session_state.openai_api_key,
            assistant_id=st.session_state.assistant_id,
        )
    st.session_state.chat.start()