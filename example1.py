import streamlit as st
from utils import Chat

st.title("Example 1")

if "chat" not in st.session_state:
    st.session_state.chat = Chat(assistant_id="asst_L3UMuNhrLspPzEOK6apTgTlW")

st.session_state.chat.show()

if prompt := st.chat_input("What is up?"):
    st.session_state.chat.respond(prompt)
