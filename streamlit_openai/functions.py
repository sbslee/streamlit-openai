import openai
import streamlit as st

from langchain_google_community import GoogleSearchAPIWrapper

class GenerateImage:
    definition = {
        "name": "generate_image",
        "description": "Generate an image based on a given prompt.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "A description of the image to be generated.",
                }
            },
            "required": ["prompt"]
        }
    }

    def function(prompt):
        response = st.session_state.chat.client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return response.data[0].url

class SearchWeb:
    definition = {
        "name": "search_web",
        "description": """Answer a question based on the content of a web search result. Do not use this function unless the user has explicitly requested to retrieve data from the web. For example, if the prompt is "What is the capital of France?", you must not use this function. However, if the prompt is "What is the capital of France? Search the web for the answer.", you can use this function.""",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The query to search the web for.",
                }
            },
            "required": ["query"]
        }
    }

    def function(query):
        search = GoogleSearchAPIWrapper()
        result = search.run(query)
        return result