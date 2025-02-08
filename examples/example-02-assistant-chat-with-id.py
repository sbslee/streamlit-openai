import streamlit as st
import streamlit_openai as so

st.title("Example 2: Assistant Chat with ID")

if "submitted" not in st.session_state:
    st.session_state.submitted = False

if not st.session_state.submitted:
    with st.form("my_form"):
        st.session_state.openai_api_key = st.text_input("OpenAI API Key", type="password")
        st.session_state.assistant_id = st.text_input("OpenAI Assistant ID", type="password")
        st.session_state.submitted = st.form_submit_button("Submit")
        if st.session_state.submitted:
            st.rerun()
else:
    if "chat" not in st.session_state:
        st.session_state.chat = so.utils.AssistantChat(
            openai_api_key=st.session_state.openai_api_key,
            assistant_id=st.session_state.assistant_id,
        )
    st.session_state.chat.start()