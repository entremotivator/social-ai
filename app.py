import os
import requests
import streamlit as st
from langchain.callbacks.base import BaseCallbackHandler
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain_community.llms import Ollama

# API Configuration
DEFAULT_API_URL = os.getenv("API_URL", "https://theaisource-u29564.vm.elestio.app:57987")
DEFAULT_USERNAME = os.getenv("API_USERNAME", "root")
DEFAULT_PASSWORD = os.getenv("API_PASSWORD", "eZfLK3X4-SX0i-UmgUBe6E")

class StreamHandler(BaseCallbackHandler):
    def __init__(self, container):
        self.container = container
        self.text = ""

    def on_llm_new_token(self, token: str, **kwargs):
        self.text += token
        self.container.markdown(self.text)

def get_ollama_models() -> list:
    try:
        response = requests.get(
            f"{DEFAULT_API_URL}/api/tags",
            auth=(DEFAULT_USERNAME, DEFAULT_PASSWORD)
        )
        if response.status_code == 200:
            models = response.json()
            return [model['name'] for model in models['models'] if 'llama:3.2' in model['name'].lower()]
        return []
    except Exception as e:
        print(f"Error fetching models: {e}")
        return []

def get_conversation_chain(model_name: str) -> ConversationChain:
    llm = Ollama(
        model=model_name,
        temperature=0.2,
        base_url=DEFAULT_API_URL,
        auth=(DEFAULT_USERNAME, DEFAULT_PASSWORD),
    )
    prompt = PromptTemplate(
        input_variables=["history", "input"], 
        template="""Current conversation:
                    {history}
                    Human: {input}
                    Assistant:""")
    memory = ConversationBufferMemory(return_messages=True)
    return ConversationChain(llm=llm, memory=memory, prompt=prompt, verbose=True)

def on_model_change():
    st.session_state.messages = []
    st.session_state.conversation = None

def run():
    st.title("Chat with Llama 3.2")

    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'conversation' not in st.session_state:
        st.session_state.conversation = None

    models = get_ollama_models()
    if not models:
        st.warning("No Llama 3.2 models available. Please check your Ollama setup.")
        return

    model_name = st.selectbox(
        "Select Llama 3.2 Model:",
        models,
        key="model_select",
        on_change=on_model_change
    )

    if st.session_state.conversation is None:
        st.session_state.conversation = get_conversation_chain(model_name)

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input(f"Chat with {model_name}"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            
            try:
                stream_handler = StreamHandler(response_placeholder)
                st.session_state.conversation.llm.callbacks = [stream_handler]
                response = st.session_state.conversation.run(prompt)
                st.session_state.conversation.llm.callbacks = []
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                error_message = f"Error generating response: {str(e)}"
                response_placeholder.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})

if __name__ == "__main__":
    run()
