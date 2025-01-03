import streamlit as st
import requests
import json
import time
import asyncio
import aiohttp
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import queue
import random
import uuid
from enum import Enum

# Data Classes and Enums
@dataclass
class Platform:
    name: str
    max_length: Optional[int]
    features: List[str]
    best_practices: List[str]
    hashtag_limit: int

@dataclass
class PostRequest:
    id: str
    platform: str
    post_type: str
    content: str
    timestamp: datetime
    status: str = "pending"
    generated_content: Optional[str] = None

class PostStatus(Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"

# Platform Configurations
PLATFORM_CONFIGS = {
    "Twitter": Platform(
        name="Twitter",
        max_length=280,
        features=["text", "images", "polls", "threads"],
        best_practices=[
            "Use relevant hashtags (1-2)",
            "Include calls to action",
            "Engage with questions",
            "Use thread for longer content"
        ],
        hashtag_limit=2
    ),
    "Instagram": Platform(
        name="Instagram",
        max_length=2200,
        features=["images", "carousel", "stories", "reels"],
        best_practices=[
            "Use up to 30 hashtags",
            "Focus on visual content",
            "Use storytelling",
            "Include strong CTA"
        ],
        hashtag_limit=30
    ),
    "LinkedIn": Platform(
        name="LinkedIn",
        max_length=3000,
        features=["text", "articles", "documents", "polls"],
        best_practices=[
            "Professional tone",
            "Industry insights",
            "Use statistics",
            "Share expertise"
        ],
        hashtag_limit=5
    ),
    "Facebook": Platform(
        name="Facebook",
        max_length=63206,
        features=["text", "images", "videos", "events"],
        best_practices=[
            "Mix media types",
            "Engage community",
            "Ask questions",
            "Share stories"
        ],
        hashtag_limit=3
    ),
    "TikTok": Platform(
        name="TikTok",
        max_length=2200,
        features=["short videos", "sounds", "effects", "challenges"],
        best_practices=[
            "Trending sounds",
            "Authentic content",
            "Creative effects",
            "Challenge participation"
        ],
        hashtag_limit=5
    )
}

class AsyncOllamaAPI:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.auth = aiohttp.BasicAuth(username, password)
        self.semaphore = asyncio.Semaphore(5)  # Limit concurrent requests
        self.timeout = aiohttp.ClientTimeout(total=None)  # No timeout

    async def generate_post(self, prompt: str, session: aiohttp.ClientSession) -> str:
        """Generate post content asynchronously."""
        async with self.semaphore:
            try:
                payload = {
                    "model": "llama3.2",
                    "messages": [
                        {"role": "system", "content": st.session_state.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": st.session_state.temperature,
                    "max_tokens": st.session_state.max_tokens,
                    "stream": False
                }

                async with session.post(
                    f"{self.base_url}/v1/chat/completions",
                    auth=self.auth,
                    json=payload,
                    timeout=self.timeout
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                return f"Error generating post: {str(e)}"

class MultiPlatformGenerator:
    def __init__(self):
        self.api = AsyncOllamaAPI(
            base_url=st.session_state.api_url,
            username=st.session_state.username,
            password=st.session_state.password
        )
        self.queue = asyncio.Queue()
        self.results = {}

    async def generate_multiple(self, prompts: List[Dict]) -> Dict[str, str]:
        """Generate multiple posts concurrently."""
        async with aiohttp.ClientSession() as session:
            tasks = []
            for prompt in prompts:
                task = asyncio.create_task(
                    self.api.generate_post(prompt["content"], session)
                )
                tasks.append((prompt["id"], task))

            results = {}
            for prompt_id, task in tasks:
                try:
                    result = await task
                    results[prompt_id] = result
                except Exception as e:
                    results[prompt_id] = f"Error: {str(e)}"

            return results

def init_session_state():
    """Initialize enhanced session state."""
    defaults = {
        "messages": [],
        "api_url": "https://theaisource-u29564.vm.elestio.app:57987",
        "username": "root",
        "password": "eZfLK3X4-SX0i-UmgUBe6E",
        "selected_model": "llama3.2",
        "temperature": 0.7,
        "max_tokens": 2000,
        "pending_generations": {},
        "completed_generations": {},
        "system_prompt": (
            "You are an expert social media strategist specializing in multi-platform "
            "content creation. Create engaging, platform-optimized content that drives "
            "meaningful engagement while following each platform's best practices."
        ),
        "business_details": {},
        "selected_platforms": set(),
        "generation_history": []
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def create_platform_prompt(platform: str, post_type: str, content: str, business_details: Dict) -> Dict:
    """Create platform-specific prompt."""
    platform_config = PLATFORM_CONFIGS[platform]
    prompt = f"""
Create a {post_type} post for {platform} with these requirements:

Platform: {platform}
Max Length: {platform_config.max_length} characters
Features Available: {', '.join(platform_config.features)}
Best Practices:
{chr(10).join('- ' + practice for practice in platform_config.best_practices)}

Business Details:
- Name: {business_details.get('name', '')}
- Industry: {business_details.get('industry', '')}
- Target Audience: {business_details.get('target_audience', '')}

Content Theme:
{content}

Requirements:
1. Follow {platform}'s best practices
2. Include up to {platform_config.hashtag_limit} relevant hashtags
3. Optimize for {platform}'s specific format
4. Match the {post_type} content style
5. Include appropriate calls to action

Please provide the post in ready-to-use format.
"""
    return {
        "id": f"{platform.lower()}_{uuid.uuid4().hex[:8]}",
        "content": prompt,
        "platform": platform
    }

async def generate_posts(platforms: Set[str], post_type: str, content: str, 
                        business_details: Dict) -> Dict[str, str]:
    """Generate posts for multiple platforms concurrently."""
    prompts = [
        create_platform_prompt(platform, post_type, content, business_details)
        for platform in platforms
    ]
    
    generator = MultiPlatformGenerator()
    results = await generator.generate_multiple(prompts)
    return results

def display_business_form():
    """Display enhanced business information form."""
    st.markdown("### 💼 Business Profile")
    col1, col2 = st.columns(2)
    
    with col1:
        name = st.text_input("Business Name")
        industry = st.selectbox(
            "Industry",
            ["Technology", "Retail", "Healthcare", "Education", "Finance", 
             "Entertainment", "Food & Beverage", "Other"]
        )
    
    with col2:
        website = st.text_input("Website")
        target_audience = st.text_input("Target Audience")

    goals = st.multiselect(
        "Business Goals",
        ["Brand Awareness", "Lead Generation", "Sales", "Community Building",
         "Customer Service", "Thought Leadership"]
    )
    
    tone = st.select_slider(
        "Brand Voice",
        options=["Professional", "Casual", "Friendly", "Authoritative", "Playful"],
        value="Professional"
    )
    
    description = st.text_area("Business Description")
    
    return {
        "name": name,
        "industry": industry,
        "website": website,
        "target_audience": target_audience,
        "goals": goals,
        "tone": tone,
        "description": description
    }

def main():
    """Enhanced main application with multi-platform support."""
    st.set_page_config(
        page_title="Multi-Platform Social Media Generator",
        page_icon="🌐",
        layout="wide"
    )
    init_session_state()
    
    st.title("🌐 Multi-Platform Social Media Generator")
    
    # Tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Create Posts", "History", "Analytics"])
    
    with tab1:
        # Platform Selection
        st.markdown("### 📱 Select Platforms")
        selected_platforms = st.multiselect(
            "Choose platforms for content generation:",
            list(PLATFORM_CONFIGS.keys()),
            default=["Twitter", "LinkedIn"]
        )
        
        if selected_platforms:
            # Display selected platform guidelines
            with st.expander("Platform Guidelines", expanded=False):
                for platform in selected_platforms:
                    st.markdown(f"#### {platform}")
                    config = PLATFORM_CONFIGS[platform]
                    st.write(f"Max Length: {config.max_length} characters")
                    st.write("Best Practices:")
                    for practice in config.best_practices:
                        st.write(f"- {practice}")
        
        # Post Type Selection
        post_type = st.selectbox(
            "Content Type",
            ["Promotional", "Informative", "Inspirational", "Engaging Question", 
             "Event Announcement", "Behind the Scenes", "User Generated Content"]
        )
        
        # Business Information
        business_details = display_business_form()
        st.session_state.business_details = business_details
        
        # Content Input
        st.markdown("### 📝 Content Creation")
        content = st.text_area(
            "What would you like to post about?",
            height=100,
            help="Describe your main message or campaign idea"
        )
        
        # Generation Settings
        with st.expander("Advanced Settings", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.temperature = st.slider(
                    "Creativity Level",
                    0.1, 1.0, 0.7, 0.1
                )
            with col2:
                st.session_state.max_tokens = st.slider(
                    "Max Length",
                    500, 4000, 2000, 100
                )
        
        # Generate Button
        if st.button("🚀 Generate Posts", disabled=not (selected_platforms and content)):
            with st.spinner("Generating posts for multiple platforms..."):
                try:
                    results = asyncio.run(
                        generate_posts(
                            set(selected_platforms),
                            post_type,
                            content,
                            business_details
                        )
                    )
                    
                    # Display Results
                    st.markdown("### 📊 Generated Posts")
                    for platform in selected_platforms:
                        with st.expander(f"{platform} Post", expanded=True):
                            post_id = next(
                                k for k in results.keys() 
                                if k.startswith(platform.lower())
                            )
                            generated_content = results[post_id]
                            
                            st.text_area(
                                "Content",
                                generated_content,
                                height=150
                            )
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(f"📋 Copy {platform} Post"):
                                    st.write(f"{platform} post copied!")
                            with col2:
                                if st.button(f"🔄 Regenerate {platform} Post"):
                                    st.write(f"Regenerating {platform} post...")
                    
                    # Save to history
                    timestamp = datetime.now()
                    for platform, content in results.items():
                        st.session_state.generation_history.append({
                            "id": platform,
                            "platform": platform.split('_')[0].capitalize(),
                            "content": content,
                            "timestamp": timestamp,
                            "type": post_type
                        })
                    
                except Exception as e:
                    st.error(f"Error during generation: {str(e)}")
    
    with tab2:
        display_history()
    
    with tab3:
        display_analytics()

def display_history():
    """Display enhanced post history."""
    if not st.session_state.generation_history:
        st.info("No generation history yet")
        return
    
    st.markdown("### 📜 Generation History")
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        platform_filter = st.multiselect(
            "Filter by Platform",
            list(PLATFORM_CONFIGS.keys()),
            default=list(PLATFORM_CONFIGS.keys())
        )
    with col2:
        date_filter = st.date_input(
            "Filter by Date",
            value=datetime.now()
        )
    
    # Display filtered history
    filtered_history = [
        post for post in st.session_state.generation_history
        if post["platform"] in platform_filter and
        post["timestamp"].date() == date_filter
    ]
    
    for post in filtered_history:
        with st.expander(
            f"{post['platform']} - {post['timestamp'].strftime('%Y-%m-%d %H:%M')}",
            expanded=False
        ):
            st.text_area(
                "Content",
                post["content"],
                height=150,
                disabled=True
            )
            st.write(f"Type: {post['type']}")
            if st.button(f"🔄 Regenerate (ID: {post['id']})"):
                st.write("Regeneration queued...")

def display_analytics():
    """Display analytics dashboard."""
    st.markdown("### 📊 Post Analytics")
    st.info("Analytics feature coming soon!")

if __name__ == "__main__":
    main()
