import streamlit as st
import requests
import time
from datetime import datetime
import os

# API configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
API_V1 = f"{API_URL}/api/v1"

st.set_page_config(
    page_title="PatternScout",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        color: #666;
        margin-bottom: 2rem;
    }
    .screenshot-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .tag {
        display: inline-block;
        background: #f0f0f0;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8rem;
        margin: 2px;
    }
</style>
""", unsafe_allow_html=True)

def main():
    st.markdown('<p class="main-header">🔍 PatternScout</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-powered UX pattern research for Product Managers</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("About")
        st.markdown("""
        PatternScout helps you:
        1. **Search** for UI patterns across the web
        2. **Analyze** screenshots with AI
        3. **Discover** patterns and generate hybrid ideas
        """)
        
        st.header("Settings")
        api_url = st.text_input("API URL", value=API_URL)
        
        st.divider()
        
        # Health check
        try:
            response = requests.get(f"{api_url}/health", timeout=5)
            if response.status_code == 200:
                st.success("✅ API Connected")
            else:
                st.error("❌ API Error")
        except:
            st.error("❌ API Unreachable")
    
    # Main content tabs
    tab1, tab2 = st.tabs(["🔍 New Search", "📊 Results"])
    
    with tab1:
        search_tab(api_url)
    
    with tab2:
        results_tab(api_url)

def search_tab(api_url):
    st.header("Start a New Search")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query = st.text_input(
            "What UI pattern are you researching?",
            placeholder="e.g., e-commerce checkout flow, mobile onboarding, variant selector",
            help="Describe the UI pattern you want to find examples of"
        )
    
    with col2:
        num_results = st.slider("Results", 5, 20, 10)
    
    if st.button("🔍 Search", type="primary", use_container_width=True):
        if not query:
            st.warning("Please enter a search query")
            return
        
        try:
            with st.spinner("Creating search job..."):
                response = requests.post(
                    f"{api_url}/api/v1/search",
                    json={"query": query, "num_results": num_results},
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.current_job_id = data["job_id"]
                    st.session_state.current_query = query
                    st.success(f"Search started! Job ID: {data['job_id']}")
                    
                    # Auto-redirect to results tab
                    st.info("Go to the **Results** tab to track progress")
                else:
                    st.error(f"Error: {response.text}")
        
        except Exception as e:
            st.error(f"Failed to start search: {e}")
    
    st.divider()
    
    # Example queries
    st.subheader("Example searches")
    examples = [
        "e-commerce checkout flow",
        "mobile app onboarding",
        "product variant selector",
        "search results page",
        "empty state design",
        "filter and sort UI"
    ]
    
    cols = st.columns(3)
    for i, example in enumerate(examples):
        with cols[i % 3]:
            if st.button(f"💡 {example}", key=f"ex_{i}"):
                st.session_state.example_query = example
                st.rerun()

def results_tab(api_url):
    st.header("Search Results")
    
    # Job ID input
    job_id = st.number_input(
        "Job ID",
        min_value=1,
        value=st.session_state.get("current_job_id", 1),
        step=1
    )
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if st.button("🔄 Refresh Status", use_container_width=True):
            st.rerun()
    
    with col2:
        if st.button("📋 Load Results", type="primary", use_container_width=True):
            st.session_state.load_results = True
            st.rerun()
    
    # Fetch and display status
    try:
        response = requests.get(
            f"{api_url}/api/v1/search/{int(job_id)}/status",
            timeout=10
        )
        
        if response.status_code == 200:
            status = response.json()
            
            # Status display
            status_color = {
                "pending": "⏳",
                "scraping": "🔍",
                "downloading": "📥",
                "analyzing": "🧠",
                "completed": "✅",
                "failed": "❌"
            }.get(status["status"], "⏳")
            
            st.subheader(f"Status: {status_color} {status['status'].upper()}")
            
            # Progress metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Screenshots", status["total_screenshots"])
            col2.metric("Analyzed", status["analyzed_screenshots"])
            
            if status["total_screenshots"] > 0:
                progress = status["analyzed_screenshots"] / status["total_screenshots"]
                col3.metric("Progress", f"{progress:.0%}")
            
            if status.get("error_message"):
                st.error(f"Error: {status['error_message']}")
            
            # Auto-refresh if still processing
            if status["status"] in ["pending", "scraping", "downloading", "analyzing"]:
                st.info("⏳ Processing... Refresh in a few seconds")
                time.sleep(2)
                st.rerun()
        
        else:
            st.error("Job not found")
    
    except Exception as e:
        st.error(f"Failed to fetch status: {e}")
    
    # Load results
    if st.session_state.get("load_results"):
        st.divider()
        st.subheader("Screenshots")
        
        try:
            response = requests.get(
                f"{api_url}/api/v1/search/{int(job_id)}/results",
                timeout=30
            )
            
            if response.status_code == 200:
                results = response.json()
                
                if not results:
                    st.info("No results yet. Wait for processing to complete.")
                else:
                    # Filter by tags
                    all_tags = set()
                    for r in results:
                        all_tags.update([t["tag"] for t in r["tags"]])
                    
                    if all_tags:
                        selected_tags = st.multiselect(
                            "Filter by tags",
                            options=sorted(all_tags)
                        )
                        
                        if selected_tags:
                            results = [
                                r for r in results
                                if any(t["tag"] in selected_tags for t in r["tags"])
                            ]
                    
                    # Display grid
                    cols = st.columns(3)
                    for i, screenshot in enumerate(results):
                        with cols[i % 3]:
                            with st.container():
                                # Image
                                if screenshot["image_url"]:
                                    st.image(
                                        screenshot["image_url"],
                                        use_container_width=True
                                    )
                                
                                # Title
                                if screenshot["title"]:
                                    st.caption(screenshot["title"][:100])
                                
                                # Source link
                                if screenshot["source_url"]:
                                    st.markdown(
                                        f"[View source]({screenshot['source_url']})"
                                    )
                                
                                # Tags
                                if screenshot["tags"]:
                                    tags_html = " ".join([
                                        f'<span class="tag">{t["tag"]}</span>'
                                        for t in screenshot["tags"][:5]
                                    ])
                                    st.markdown(tags_html, unsafe_allow_html=True)
                                
                                # Description
                                if screenshot["description"]:
                                    with st.expander("📝 Analysis"):
                                        st.write(screenshot["description"])
                                
                                st.divider()
            
            else:
                st.error("Failed to load results")
        
        except Exception as e:
            st.error(f"Error loading results: {e}")

if __name__ == "__main__":
    main()
