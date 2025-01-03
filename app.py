import streamlit as st
import requests
from typing import List, Dict
import json
from datetime import datetime

# Initialize session state
def initialize_session_state():
    default_values = {
        "messages": [],
        "api_configured": False,
        "api_url": "https://theaisource-u29564.vm.elestio.app:57987",
        "username": "root",
        "password": "eZfLK3X4-SX0i-UmgUBe6E",
        "selected_model": "llama3.2",
        "bot_personality": "You are a creative assistant specializing in crafting engaging social media posts."
    }
    for key, value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = value

initialize_session_state()

def send_message_to_ollama(message: str, include_context: bool = True) -> Dict:
    try:
        headers = {"Content-Type": "application/json"}
        context = [{"role": msg["role"], "content": msg["content"]} for msg in st.session_state.messages] if include_context else []
        payload = {
            "prompt": message,
            "model": st.session_state.selected_model,
            "stream": False,
            "context": context,
        }
        response = requests.post(
            f"{st.session_state.api_url}/api/generate",
            auth=(st.session_state.username, st.session_state.password),
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_message = f"API Error: {str(e)}"
        st.error(error_message)
        return {"response": error_message}

# Main application
def main():
    st.set_page_config(
        page_title="Social Media Post Generator",
        page_icon="🌐",
        layout="wide"
    )

    st.title("🌐 Social Media Post Generator")

    # Sidebar for configuration
    with st.sidebar:
        st.markdown("### API Configuration")
        with st.expander("Configure API Settings"):
            new_api_url = st.text_input("API URL", value=st.session_state.api_url, type="password")
            new_username = st.text_input("Username", value=st.session_state.username, type="password")
            new_password = st.text_input("Password", value=st.session_state.password, type="password")
            if st.button("Update API Settings"):
                if new_api_url and new_username and new_password:
                    st.session_state.api_url = new_api_url
                    st.session_state.username = new_username
                    st.session_state.password = new_password
                    st.success("API settings updated!")
                else:
                    st.error("Please fill in all API settings fields.")

        st.markdown("### Bot Personality")
        st.session_state.bot_personality = st.text_area(
            "Customize Bot Personality",
            value=st.session_state.bot_personality
        )
        st.markdown("### Chat Controls")
        if st.button("Clear Post History"):
            st.session_state.messages = []
            st.success("Post history cleared!")

    # Main content
    platform = st.selectbox("Choose a platform for your post:", ["Instagram", "Twitter", "LinkedIn", "Facebook", "TikTok"])
    post_type = st.selectbox("Select post type:", ["Promotional", "Informative", "Inspirational", "Engaging Question", "Event Announcement"])
    character_limit = 280 if platform == "Twitter" else None

    st.markdown("---")

    emojis = {
        "Inspirational": ["✨", "🌟", "💪", "🔥", "🌈"],
        "Promotional": ["🎉", "💼", "🛍️", "📢", "💰"],
        "Informative": ["📚", "🧠", "💡", "📊", "🔍"],
        "Engaging Question": ["❓", "🤔", "💬", "🔑", "🎯"],
        "Event Announcement": ["📅", "📢", "🎶", "🎈", "📸"]
    }

    st.markdown("### Business Information")
    business_name = st.text_input("Enter your business name:", placeholder="Your Business Name")
    business_info = st.text_area("Enter your business information:", placeholder="Brief description of your business")

    if prompt := st.text_area("Enter your idea or theme for the post:"):
        emoji_options = "".join(emojis.get(post_type, []))
        prompt_with_context = (
            f"Platform: {platform}\n"
            f"Post Type: {post_type}\n"
            f"Character Limit: {character_limit or 'No Limit'}\n"
            f"Emojis: {emoji_options}\n"
            f"Business Name: {business_name}\n"
            f"Business Info: {business_info}\n\n"
            f"{prompt}"
        )
        st.session_state.messages.append({
            "role": "user",
            "content": prompt_with_context,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        with st.spinner(f"Generating post for {platform}..."):
            response = send_message_to_ollama(prompt_with_context)
            generated_post = response.get("response", "Unable to generate post.")

        st.markdown("### Generated Post")
        st.text_area("Your Social Media Post:", generated_post, height=150)

        st.session_state.messages.append({
            "role": "assistant",
            "content": generated_post,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        if st.button("Save Post"):
            st.success("Post saved to history!")

    # Display post history
    st.markdown("---")
    st.markdown("### Post History")
    for message in st.session_state.messages:
        st.write(f"{message['timestamp']} - {message['role'].capitalize()}:")
        st.text_area("", message["content"], height=100, disabled=True)

if __name__ == "__main__":
    main()
