import streamlit as st
import requests
import json
import time
from typing import Dict, Optional, Tuple, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import threading
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import queue

class OllamaAPI:
    def __init__(self, base_url: str, username: str, password: str, timeout: int = 90):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.timeout = timeout
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a session with retry strategy."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.auth = (self.username, self.password)
        return session

    def _make_request(self, payload: Dict) -> Dict:
        """Make request with timeout handling."""
        headers = {"Content-Type": "application/json"}
        try:
            response = self.session.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            raise TimeoutError("Request timed out")
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")

    def generate_with_backup(self, messages: List[Dict], temperature: float = 0.7) -> Tuple[str, Dict]:
        """Generate response with backup settings if primary fails."""
        payloads = [
            {
                "model": "llama3.2",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 2000,
                "stream": False
            },
            # Backup settings with lower complexity
            {
                "model": "llama3.2",
                "messages": messages,
                "temperature": 0.5,
                "max_tokens": 1000,
                "stream": False
            }
        ]

        for payload in payloads:
            try:
                response = self._make_request(payload)
                content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                return content, response
            except Exception as e:
                last_error = str(e)
                continue

        raise Exception(f"All generation attempts failed. Last error: {last_error}")

class PostGenerator:
    def __init__(self):
        self.api = OllamaAPI(
            base_url=st.session_state.api_url,
            username=st.session_state.username,
            password=st.session_state.password
        )

    def generate_post(self, prompt: str, platform: str, post_type: str) -> str:
        """Generate post with progress tracking."""
        messages = [
            {"role": "system", "content": st.session_state.system_prompt},
            {"role": "user", "content": prompt}
        ]

        try:
            content, response = self.api.generate_with_backup(messages, st.session_state.temperature)
            return content
        except Exception as e:
            st.error(f"Error generating post: {str(e)}")
            return "Unable to generate post. Please try again."

def init_session_state():
    """Initialize session state variables."""
    defaults = {
        "messages": [],
        "api_url": "https://theaisource-u29564.vm.elestio.app:57987",
        "username": "root",
        "password": "eZfLK3X4-SX0i-UmgUBe6E",
        "selected_model": "llama3.2",
        "temperature": 0.7,
        "max_tokens": 2000,
        "generation_queue": queue.Queue(),
        "system_prompt": (
            "You are an expert social media manager with deep knowledge of each "
            "platform's best practices, audience behavior, and content optimization. "
            "Create engaging, platform-specific content that drives meaningful engagement."
        )
    }
   
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def get_platform_specific_content(platform: str, post_type: str, industry: str) -> Dict[str, str]:
    """Get platform-specific content guidelines and best practices."""
    return {
        "character_limit": "280" if platform == "Twitter" else "Unlimited",
        "best_practices": PLATFORM_GUIDELINES[platform],
        "industry_tips": INDUSTRY_GUIDELINES.get(industry, ""),
        "content_type_tips": POST_TYPE_GUIDELINES[post_type],
        "hashtag_suggestions": HASHTAG_SUGGESTIONS.get(platform, [])
    }

# Constants
PLATFORM_GUIDELINES = {
    "Twitter": {
        "format": "Short, concise posts limited to 280 characters",
        "media": "Support for images, videos, polls, and threads",
        "engagement": "Use hashtags, mentions, and encourage retweets"
    },
    "Instagram": {
        "format": "Visual-first platform with support for carousel posts",
        "media": "High-quality images and videos are essential",
        "engagement": "Use up to 30 relevant hashtags, encourage saves and shares"
    },
    # Add other platforms...
}

INDUSTRY_GUIDELINES = {
    "Technology": {
        "tone": "Professional yet innovative",
        "topics": ["Industry trends", "Product launches", "Tech tips", "Innovation stories"],
        "content_mix": "40% educational, 30% promotional, 30% engagement"
    },
    # Add other industries...
}

POST_TYPE_GUIDELINES = {
    "Promotional": {
        "structure": "Hook → Value Prop → Social Proof → CTA",
        "tips": ["Use action words", "Create urgency", "Highlight benefits"]
    },
    # Add other post types...
}

HASHTAG_SUGGESTIONS = {
    "Twitter": ["#tech", "#innovation", "#business"],
    "Instagram": ["#instagood", "#photooftheday", "#business"],
    # Add other platforms...
}

def render_sidebar():
    """Render enhanced sidebar with advanced settings."""
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
       
        # API Settings
        with st.expander("API Settings"):
            st.text_input("API URL", value=st.session_state.api_url, key="api_url_input")
            st.text_input("Username", value=st.session_state.username, key="username_input")
            st.text_input("Password", value=st.session_state.password, type="password", key="password_input")
            st.text_input("Model", value=st.session_state.selected_model, key="model_input")

        # Advanced Settings
        with st.expander("Advanced Settings"):
            st.slider("Temperature", 0.1, 1.0, st.session_state.temperature, 0.1, key="temperature_slider")
            st.slider("Max Tokens", 100, 4000, st.session_state.max_tokens, 100, key="max_tokens_slider")
            st.text_area("System Prompt", value=st.session_state.system_prompt, key="system_prompt_input")

        # History Management
        with st.expander("History Management"):
            if st.button("Clear History"):
                st.session_state.messages = []
                st.success("History cleared!")
           
            if st.button("Export History"):
                export_history()

def export_history():
    """Export post history to JSON."""
    if st.session_state.messages:
        export_data = {
            "messages": st.session_state.messages,
            "export_date": datetime.now().isoformat()
        }
        st.download_button(
            "Download History",
            data=json.dumps(export_data, indent=2),
            file_name=f"post_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

def main():
    """Enhanced main application function."""
    st.set_page_config(
        page_title="Professional Social Media Post Generator",
        page_icon="🌐",
        layout="wide"
    )
    init_session_state()
   
    st.title("🌐 Professional Social Media Post Generator")
    render_sidebar()

    # Main content area with tabs
    tab1, tab2, tab3 = st.tabs(["Create Post", "Post History", "Analytics"])

    with tab1:
        create_post_interface()

    with tab2:
        display_post_history()

    with tab3:
        display_analytics()

def create_post_interface():
    """Create post interface with enhanced features."""
    col1, col2 = st.columns([2, 1])

    with col1:
        platform = st.selectbox(
            "Platform",
            ["Twitter", "Instagram", "LinkedIn", "Facebook", "TikTok"]
        )
        post_type = st.selectbox(
            "Content Type",
            ["Promotional", "Informative", "Inspirational", "Engaging Question", "Event Announcement"]
        )

    with col2:
        industry = st.selectbox(
            "Industry",
            list(INDUSTRY_GUIDELINES.keys()) + ["Other"]
        )

    # Get platform-specific content
    content_guidelines = get_platform_specific_content(platform, post_type, industry)
   
    with st.expander("📝 Content Guidelines", expanded=True):
        st.json(content_guidelines)

    # Business details
    st.markdown("### 💼 Business Information")
    business_details = get_business_details()

    # Post content
    st.markdown("### 📱 Post Content")
    prompt = st.text_area("What would you like to post about?", height=100)

    if st.button("Generate Post"):
        with st.spinner("Generating your post..."):
            try:
                generator = PostGenerator()
                post = generator.generate_post(
                    create_detailed_prompt(prompt, platform, post_type, business_details, content_guidelines),
                    platform,
                    post_type
                )
                display_generated_post(post, platform)
            except Exception as e:
                st.error(f"Failed to generate post: {str(e)}")

def get_business_details() -> Dict[str, str]:
    """Get business details from user input."""
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Business Name")
        website = st.text_input("Website")
    with col2:
        target_audience = st.text_input("Target Audience")
        goals = st.multiselect(
            "Business Goals",
            ["Brand Awareness", "Lead Generation", "Sales", "Community Building"]
        )
   
    description = st.text_area("Business Description")
   
    return {
        "name": name,
        "website": website,
        "target_audience": target_audience,
        "goals": goals,
        "description": description
    }

def create_detailed_prompt(prompt: str, platform: str, post_type: str,
                         business_details: Dict[str, str], guidelines: Dict[str, str]) -> str:
    """Create a detailed prompt for the AI."""
    return f"""
Platform: {platform}
Post Type: {post_type}
Business: {business_details['name']}

Guidelines:
{json.dumps(guidelines, indent=2)}

Business Details:
{json.dumps(business_details, indent=2)}

Content Request:
{prompt}

Please create a {post_type} post for {platform} that:
1. Follows the platform's best practices
2. Matches the specified content type
3. Aligns with business goals
4. Engages the target audience
5. Includes relevant hashtags
"""

def display_generated_post(post: str, platform: str):
    """Display generated post with platform-specific preview."""
    st.markdown("### 📝 Generated Post")
   
    # Display post
    st.text_area("Post Content", post, height=200)
   
    # Action buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("💾 Save Post"):
            save_post(post)
    with col2:
        if st.button("🔄 Regenerate"):
            st.experimental_rerun()
    with col3:
        if st.button("📋 Copy to Clipboard"):
            st.write("Post copied to clipboard!")

def save_post(post: str):
    """Save post to history with metadata."""
    st.session_state.messages.append({
        "content": post,
        "timestamp": datetime.now().isoformat(),
        "platform": st.session_state.get("platform"),
        "post_type": st.session_state.get("post_type"),
        "metrics": {
            "estimated_reach": 0,
            "potential_engagement": 0
        }
    })
    st.success("Post saved to history!")

def display_post_history():
    """Display post history with enhanced features."""
    if not st.session_state.messages:
        st.info("No posts in history yet.")
        return

    for post in reversed(st.session_state.messages):
        with st.expander(f"Post from {post['timestamp']}", expanded=False):
            st.text_area("Content", post["content"], height=150)
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"Platform: {post.get('platform', 'N/A')}")
            with col2:
                st.write(f"Type: {post.get('post_type', 'N/A')}")

def display_analytics():
    """Display analytics dashboard."""
    st.markdown("### 📊 Post Analytics")
    st.info("Analytics feature coming soon!")

if __name__ == "__main__":
    main()
