import streamlit as st
import requests
import json
from typing import Dict
from datetime import datetime

# Set Streamlit page configuration
st.set_page_config(
    page_title="Social Media Post Generator",
    page_icon="🌐",
    layout="wide"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "api_configured" not in st.session_state:
    st.session_state.api_configured = False

# Default API settings
DEFAULT_API_URL = "https://theaisource-u29564.vm.elestio.app:57987"
DEFAULT_USERNAME = "root"
DEFAULT_PASSWORD = "eZfLK3X4-SX0i-UmgUBe6E"

# Initialize API config
def initialize_api_config():
    st.session_state.api_url = st.session_state.get("api_url", DEFAULT_API_URL)
    st.session_state.username = st.session_state.get("username", DEFAULT_USERNAME)
    st.session_state.password = st.session_state.get("password", DEFAULT_PASSWORD)
    st.session_state.selected_model = st.session_state.get("selected_model", "llama3.2")
    st.session_state.bot_personality = st.session_state.get(
        "bot_personality",
        "You are a creative assistant specializing in crafting engaging social media posts."
    )

def send_message_to_ollama(message: str, include_context: bool = True) -> Dict:
    try:
        headers = {"Content-Type": "application/json"}
        context = [{"role": msg["role"], "content": msg["content"]} for msg in st.session_state.messages] if include_context else []
        payload = {
            "model": st.session_state.selected_model,
            "prompt": message,
            "stream": False,
            "context": context,
            "format": {
                "type": "object",
                "properties": {
                    "post": {
                        "type": "string"
                    },
                    "hashtags": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": ["post", "hashtags"]
            }
        }
        response = requests.post(
            f"{st.session_state.api_url}/api/generate",
            auth=(st.session_state.username, st.session_state.password),
            headers=headers,
            json=payload,
            timeout=None  # Remove timeout to prevent timeouts
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to API: {e}")
        return {"error": str(e)}

def main():
    initialize_api_config()
    st.title("🌐 Social Media Post Generator")

    # Sidebar for configuration
    with st.sidebar:
        st.markdown("### API Configuration")
        with st.expander("Configure API Settings"):
            st.session_state.api_url = st.text_input("API URL", st.session_state.api_url, type="password")
            st.session_state.username = st.text_input("Username", st.session_state.username, type="password")
            st.session_state.password = st.text_input("Password", st.session_state.password, type="password")

        # Bot personality
        st.markdown("### Bot Personality")
        st.session_state.bot_personality = st.text_area(
            "Customize Bot Personality",
            value=st.session_state.bot_personality
        )

        # Clear history
        if st.button("Clear Post History"):
            st.session_state.messages = []
            st.success("Post history cleared!")

    # Main content
    platform = st.selectbox("Choose a platform for your post:", ["Instagram", "Twitter", "LinkedIn", "Facebook", "TikTok"])
    post_type = st.selectbox("Select post type:", ["Promotional", "Informative", "Inspirational", "Engaging Question", "Event Announcement"])
    character_limit = 280 if platform == "Twitter" else None

    st.markdown("### Business Information")
    business_name = st.text_input("Enter your business name:", placeholder="Your Business Name")
    business_info = st.text_area("Enter your business information:", placeholder="Brief description of your business")

    if prompt := st.text_area("Enter your idea or theme for the post:"):
        emoji_options = {
            "Inspirational": "✨🌟💪🔥🌈",
            "Promotional": "🎉💼🛍️📢💰",
            "Informative": "📚🧠💡📊🔍",
            "Engaging Question": "❓🤔💬🔑🎯",
            "Event Announcement": "📅📢🎶🎈📸"
        }.get(post_type, "")

        prompt_with_context = (
            f"{st.session_state.bot_personality}\n\n"
            f"Platform: {platform}\n"
            f"Post Type: {post_type}\n"
            f"Character Limit: {character_limit or 'No Limit'}\n"
            f"Emojis: {emoji_options}\n"
            f"Business Name: {business_name}\n"
            f"Business Info: {business_info}\n\n"
            f"Generate a social media post based on this idea: {prompt}\n"
            f"Provide the post content and relevant hashtags in JSON format."
        )

        st.session_state.messages.append({
            "role": "user",
            "content": prompt_with_context,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        st.markdown("### Generated Post")
        with st.spinner(f"Generating post for {platform}..."):
            response = send_message_to_ollama(prompt_with_context)
            if "error" in response:
                st.error(f"Error: {response['error']}")
            else:
                st.text_area("Your Social Media Post:", response.get("post", ""), height=150)
                st.write("Hashtags: " + ", ".join(response.get("hashtags", [])))

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": json.dumps(response),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                if st.button("Save Post"):
                    st.success("Post saved to history!")

    # Display post history
    if st.session_state.messages:
        st.markdown("### Post History")
        for message in st.session_state.messages:
            st.write(f"{message['timestamp']} - {message['role'].capitalize()}:")
            if message['role'] == 'assistant':
                try:
                    content = json.loads(message['content'])
                    st.text_area("Post:", content.get('post', ''), height=100, disabled=True)
                    st.write("Hashtags:", ", ".join(content.get('hashtags', [])))
                except json.JSONDecodeError:
                    st.text_area("", message['content'], height=100, disabled=True)
            else:
                st.text_area("", message['content'], height=100, disabled=True)

if __name__ == "__main__":
    main()
