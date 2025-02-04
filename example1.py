import streamlit as st
from utils import Chat

st.title("Example 1")

if "chat" not in st.session_state:
    st.session_state.chat = Chat(assistant_id="asst_L3UMuNhrLspPzEOK6apTgTlW")

print(len(st.session_state.chat.containers))

for container in st.session_state.chat.containers:
    print('@@@@')
    container.write()

if prompt := st.chat_input("What is up?"):
    st.session_state.chat.add_user_input(prompt)
    st.session_state.chat.write()