import streamlit as st
import requests
import json
from typing import Dict, Optional
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
        "temperature": 0.7,
        "max_tokens": 2000,
        "system_prompt": ("You are an expert social media manager specializing in creating "
                        "engaging, platform-specific content that drives engagement and conversions. "
                        "Create content that matches each platform's best practices and tone.")
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def send_message_to_ollama(user_message: str) -> Dict:
    """Send message to Ollama API with error handling."""
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {st.session_state.username}:{st.session_state.password}"
        }
        
        messages = [
            {"role": "system", "content": st.session_state.system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        payload = {
            "model": st.session_state.selected_model,
            "messages": messages,
            "stream": False,
            "temperature": st.session_state.temperature,
            "max_tokens": st.session_state.max_tokens
        }
        
        response = requests.post(
            f"{st.session_state.api_url}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
            auth=(st.session_state.username, st.session_state.password)
        )
        response.raise_for_status()
        
        # Log API response for debugging
        st.session_state.last_api_response = response.json()
        
        return {"response": response.json().get("choices", [{}])[0].get("message", {}).get("content", "")}
    
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
                type="default"
            )
            st.session_state.username = st.text_input(
                "Username", 
                st.session_state.username,
                type="default"
            )
            st.session_state.password = st.text_input(
                "Password", 
                st.session_state.password,
                type="password"
            )
            st.session_state.selected_model = st.text_input(
                "Model Name",
                st.session_state.selected_model
            )
            
        st.markdown("### 🎯 Generation Settings")
        st.session_state.temperature = st.slider(
            "Temperature (Creativity)",
            min_value=0.1,
            max_value=1.0,
            value=0.7,
            step=0.1
        )
        st.session_state.max_tokens = st.slider(
            "Max Tokens",
            min_value=100,
            max_value=4000,
            value=2000,
            step=100
        )
        
        st.markdown("### 🤖 System Prompt")
        st.session_state.system_prompt = st.text_area(
            "Customize AI Behavior",
            st.session_state.system_prompt,
            height=100
        )

        if st.button("🗑️ Clear History"):
            st.session_state.messages = []
            st.success("History cleared!")

def get_platform_guidelines(platform: str) -> str:
    """Get platform-specific posting guidelines."""
    guidelines = {
        "Twitter": "280 character limit, hashtags, engaging questions, threads possible",
        "Instagram": "Visual focus, hashtags, emoji-friendly, casual tone",
        "LinkedIn": "Professional tone, industry insights, longer form possible",
        "Facebook": "Mix of casual/professional, good for long-form, engagement focus",
        "TikTok": "Trendy, casual, youth-focused, hashtag challenges"
    }
    return guidelines.get(platform, "")

def get_post_type_suggestions(post_type: str) -> str:
    """Get suggestions based on post type."""
    suggestions = {
        "Promotional": "Include clear CTA, highlight benefits, create urgency",
        "Informative": "Share insights, use data, establish authority",
        "Inspirational": "Tell stories, use emotional appeals, motivate action",
        "Engaging Question": "Ask open-ended questions, encourage discussion",
        "Event Announcement": "Include key details, create excitement, clear next steps"
    }
    return suggestions.get(post_type, "")

def main():
    """Main application function."""
    st.set_page_config(
        page_title="Professional Social Media Post Generator",
        page_icon="🌐",
        layout="wide"
    )
    init_session_state()
    
    st.title("🌐 Professional Social Media Post Generator")
    st.markdown("Create engaging, platform-optimized social media content")
    
    render_sidebar()

    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        platform = st.selectbox(
            "Choose your platform:", 
            ["Instagram", "Twitter", "LinkedIn", "Facebook", "TikTok"]
        )
        platform_info = get_platform_guidelines(platform)
        st.info(f"📝 Platform Guidelines: {platform_info}")
        
        post_type = st.selectbox(
            "Select content type:", 
            ["Promotional", "Informative", "Inspirational", "Engaging Question", "Event Announcement"]
        )
        post_type_info = get_post_type_suggestions(post_type)
        st.info(f"💡 Content Tips: {post_type_info}")

    with col2:
        st.markdown("### 💼 Business Details")
        business_name = st.text_input(
            "Business name:",
            placeholder="e.g., TechCorp Solutions"
        )
        industry = st.selectbox(
            "Industry:",
            ["Technology", "Retail", "Healthcare", "Education", "Finance", "Other"]
        )

    business_info = st.text_area(
        "Business description:",
        placeholder="Describe your business, target audience, and unique value proposition..."
    )

    target_audience = st.text_input(
        "Target audience:",
        placeholder="e.g., Tech-savvy professionals aged 25-45"
    )

    # Post generation
    prompt = st.text_area(
        "What would you like to post about?",
        placeholder="Enter your main message or campaign idea..."
    )
    
    if prompt:
        detailed_prompt = f"""
Create a {post_type} post for {platform} about:

Business: {business_name}
Industry: {industry}
Target Audience: {target_audience}
Description: {business_info}

Main Message: {prompt}

Please consider:
1. {platform}'s best practices and format
2. The {post_type} content style
3. Appropriate tone for {industry} industry
4. Appeal to: {target_audience}

Response should be in the exact format ready to post."""

        st.session_state.messages.append({
            "role": "user",
            "content": detailed_prompt,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        with st.spinner(f"✨ Crafting your {platform} post..."):
            response = send_message_to_ollama(detailed_prompt)
            generated_post = response.get("response", "Unable to generate post.")

        st.markdown("### 📝 Your Generated Post")
        post_area = st.text_area(
            "Generated Content:", 
            generated_post,
            height=200,
            key="generated_post"
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Post"):
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": generated_post,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                st.success("Post saved to history!")
        
        with col2:
            if st.button("🔄 Generate Another Version"):
                st.experimental_rerun()

    # Display history
    if st.session_state.messages:
        st.markdown("### 📜 Post History")
        for message in reversed(st.session_state.messages[-10:]):  # Show last 10 posts
            with st.expander(f"{message['timestamp']} - {message['role'].capitalize()}"):
                st.text_area(
                    "",
                    message["content"],
                    height=150,
                    disabled=True,
                    key=f"history_{message['timestamp']}"
                )

if __name__ == "__main__":
    main()
