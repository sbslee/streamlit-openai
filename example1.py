import streamlit as st
import os
import openai
from functions import GenerateImage
from utils import Chat

st.title("Example 1")

client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

if "chat" not in st.session_state:
    st.session_state.chat = Chat(assistant_id="asst_L3UMuNhrLspPzEOK6apTgTlW")

for container in st.session_state.chat.containers:
    container.write()

if prompt := st.chat_input("What is up?"):
    st.session_state.chat.write()