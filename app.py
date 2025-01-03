import streamlit as st
import requests
from typing import List, Dict, Optional
from datetime import datetime

def init_session_state():
    """Initialize session state variables if they don't exist."""
    defaults = {
        "messages": [],
        "api_configured": False,
        "api_url": "https://theaisource-u29564.vm.elestio.app:57987",
        "username": "root",
        "password": "eZfLK3X4-SX0i-UmgUBe6E",
        "selected_model": "llama3.2",
        "bot_personality": "You are a creative assistant specializing in crafting engaging social media posts."
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def send_message_to_ollama(message: str, include_context: bool = True) -> Dict:
    """Send message to Ollama API with error handling."""
    try:
        headers = {"Content-Type": "application/json"}
        context = (
            [{"role": msg["role"], "content": msg["content"]} 
             for msg in st.session_state.messages]
            if include_context else []
        )
        
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
    
    except requests.exceptions.Timeout:
        st.error("⚠️ Request timed out. Please try again.")
        return {"response": "Error: Request timed out."}
    except requests.exceptions.HTTPError as e:
        st.error(f"⚠️ HTTP error: {str(e)}")
        return {"response": f"Error: {str(e)}"}
    except requests.exceptions.RequestException as e:
        st.error(f"⚠️ Connection error: {str(e)}")
        return {"response": f"Error: {str(e)}"}
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {str(e)}")
        return {"response": f"Error: {str(e)}"}

def render_sidebar():
    """Render sidebar configuration options."""
    with st.sidebar:
        st.markdown("### ⚙️ API Configuration")
        with st.expander("Configure API Settings"):
            st.session_state.api_url = st.text_input(
                "API URL", 
                st.session_state.api_url, 
                type="password"
            )
            st.session_state.username = st.text_input(
                "Username", 
                st.session_state.username, 
                type="password"
            )
            st.session_state.password = st.text_input(
                "Password", 
                st.session_state.password, 
                type="password"
            )

        st.markdown("### 🤖 Bot Personality")
        st.session_state.bot_personality = st.text_area(
            "Customize Bot Personality",
            value=st.session_state.bot_personality
        )

        if st.button("🗑️ Clear Post History"):
            st.session_state.messages = []
            st.success("Post history cleared!")

def get_emoji_options(post_type: str) -> str:
    """Get relevant emojis based on post type."""
    emoji_map = {
        "Inspirational": "✨🌟💪🔥🌈",
        "Promotional": "🎉💼🛋️📢💰",
        "Informative": "📚🧠💡📊🔍",
        "Engaging Question": "❓🤔💬🔑🎯",
        "Event Announcement": "📅📢🎶🎈📸"
    }
    return emoji_map.get(post_type, "")

def display_post_history():
    """Display the history of generated posts."""
    if st.session_state.messages:
        st.markdown("### 📜 Post History")
        for message in st.session_state.messages:
            col1, col2 = st.columns([1, 4])
            with col1:
                st.write(f"**{message['timestamp']}**")
                st.write(f"*{message['role'].capitalize()}*")
            with col2:
                st.text_area(
                    "", 
                    message["content"], 
                    height=100, 
                    disabled=True,
                    key=f"history_{message['timestamp']}"
                )

def main():
    """Main application function."""
    # Initialize session state and page config
    st.set_page_config(
        page_title="Social Media Post Generator",
        page_icon="🌐",
        layout="wide"
    )
    init_session_state()
    
    st.title("🌐 Social Media Post Generator")
    render_sidebar()

    # Main content
    platform = st.selectbox(
        "Choose a platform:", 
        ["Instagram", "Twitter", "LinkedIn", "Facebook", "TikTok"]
    )
    
    post_type = st.selectbox(
        "Select post type:", 
        ["Promotional", "Informative", "Inspirational", "Engaging Question", "Event Announcement"]
    )
    
    character_limit = 280 if platform == "Twitter" else None

    # Business information section
    st.markdown("### 💼 Business Information")
    business_name = st.text_input(
        "Business name:",
        placeholder="Your Business Name"
    )
    business_info = st.text_area(
        "Business description:",
        placeholder="Brief description of your business"
    )

    # Post generation
    prompt = st.text_area("Enter your post idea or theme:")
    if prompt:
        emoji_options = get_emoji_options(post_type)
        prompt_with_context = f"""
Platform: {platform}
Post Type: {post_type}
Character Limit: {character_limit or 'No Limit'}
Emojis: {emoji_options}
Business Name: {business_name}
Business Info: {business_info}

{prompt}
"""

        st.session_state.messages.append({
            "role": "user",
            "content": prompt_with_context,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        with st.spinner(f"✨ Generating post for {platform}..."):
            response = send_message_to_ollama(prompt_with_context)
            generated_post = response.get("response", "Unable to generate post.")

        st.markdown("### 📝 Generated Post")
        st.text_area(
            "Your Social Media Post:", 
            generated_post, 
            height=150,
            key="generated_post"
        )

        st.session_state.messages.append({
            "role": "assistant",
            "content": generated_post,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        if st.button("💾 Save Post"):
            st.success("Post saved to history!")

    display_post_history()

if __name__ == "__main__":
    main()
