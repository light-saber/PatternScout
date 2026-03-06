import streamlit as st
import requests
import time
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

    if "example_query" not in st.session_state:
        st.session_state.example_query = ""
    if "search_query_input" not in st.session_state:
        st.session_state.search_query_input = st.session_state.example_query
    if st.session_state.get("pending_example_fill"):
        st.session_state.search_query_input = st.session_state.example_query
        st.session_state.pending_example_fill = False
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query = st.text_input(
            "What UI pattern are you researching?",
            placeholder="e.g., e-commerce checkout flow, mobile onboarding, variant selector",
            help="Describe the UI pattern you want to find examples of",
            key="search_query_input",
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
                    st.session_state.loaded_job_id = None
                    st.session_state.hybrid_idea_by_job = {}
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
                st.session_state.pending_example_fill = True
                st.rerun()

def results_tab(api_url):
    st.header("Search Results")
    previous_job_id = st.session_state.get("results_job_id", st.session_state.get("current_job_id", 1))
    
    # Job ID input
    job_id = st.number_input(
        "Job ID",
        min_value=1,
        value=previous_job_id,
        step=1,
        key="results_job_id",
    )
    job_id = int(job_id)

    if st.session_state.get("active_results_job_id") != job_id:
        st.session_state.active_results_job_id = job_id
        st.session_state.hybrid_idea = st.session_state.get("hybrid_idea_by_job", {}).get(job_id)
        st.session_state[f"source_filter_{job_id}"] = "All"
        st.session_state[f"status_filter_{job_id}"] = "All"
        st.session_state[f"sort_by_{job_id}"] = "Newest"
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if st.button("🔄 Refresh Status", use_container_width=True):
            st.rerun()
    
    with col2:
        if st.button("📋 Load Results", type="primary", use_container_width=True):
            st.session_state.loaded_job_id = job_id
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
    if st.session_state.get("loaded_job_id") == job_id:
        st.divider()
        st.subheader("Screenshots")

        filter_col1, filter_col2, filter_col3 = st.columns(3)
        with filter_col1:
            selected_source = st.selectbox(
                "Source",
                options=["All", "pageflows", "google_images"],
                key=f"source_filter_{job_id}",
            )
        with filter_col2:
            selected_status = st.selectbox(
                "Analysis",
                options=["All", "completed", "pending", "failed"],
                key=f"status_filter_{job_id}",
            )
        with filter_col3:
            sort_by = st.selectbox(
                "Sort",
                options=["Newest", "Oldest", "Title A-Z", "Title Z-A", "Source", "Status"],
                key=f"sort_by_{job_id}",
            )

        params = {}
        if selected_source != "All":
            params["source_type"] = selected_source
        if selected_status != "All":
            params["analysis_status"] = selected_status

        sort_mapping = {
            "Newest": ("created_at", "desc"),
            "Oldest": ("created_at", "asc"),
            "Title A-Z": ("title", "asc"),
            "Title Z-A": ("title", "desc"),
            "Source": ("source_type", "asc"),
            "Status": ("analysis_status", "asc"),
        }
        params["sort_by"], params["sort_order"] = sort_mapping[sort_by]
        
        try:
            response = requests.get(
                f"{api_url}/api/v1/search/{int(job_id)}/results",
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                results = response.json()
                
                if not results:
                    st.info("No results yet. Wait for processing to complete.")
                else:
                    stats_col1, stats_col2, stats_col3 = st.columns(3)
                    stats_col1.metric("Visible Results", len(results))
                    stats_col2.metric("Sources", len({r["source_type"] for r in results}))
                    stats_col3.metric(
                        "Completed Analyses",
                        sum(1 for r in results if r["analysis_status"] == "completed")
                    )

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

                    st.divider()
                    st.subheader("Pattern Clusters")
                    try:
                        cluster_response = requests.get(
                            f"{api_url}/api/v1/search/{int(job_id)}/clusters",
                            params={"min_cluster_size": 1, "max_clusters": 10},
                            timeout=20
                        )
                        if cluster_response.status_code == 200:
                            clusters = cluster_response.json()
                            if not clusters:
                                st.info("No clusters available yet.")
                            else:
                                for c in clusters:
                                    st.markdown(f"**{c['pattern_name']}** ({c['count']} examples)")
                                    if c.get("common_tags"):
                                        st.caption("Tags: " + ", ".join(c["common_tags"][:8]))
                        else:
                            st.warning("Could not load clusters.")
                    except Exception as e:
                        st.warning(f"Cluster fetch failed: {e}")

                    st.divider()
                    st.subheader("Generate Hybrid Idea")

                    options = {
                        f"{r['id']} - {(r.get('title') or 'Untitled')[:70]}": r["id"]
                        for r in results
                    }
                    selected_labels = st.multiselect(
                        "Select screenshots for hybrid generation",
                        options=list(options.keys()),
                        default=list(options.keys())[:3]
                    )
                    selected_ids = [options[label] for label in selected_labels]

                    if st.button("🧪 Generate Hybrid", type="primary", key=f"hybrid_{job_id}"):
                        if len(selected_ids) < 2:
                            st.warning("Select at least 2 screenshots.")
                        else:
                            try:
                                hybrid_response = requests.post(
                                    f"{api_url}/api/v1/search/{int(job_id)}/hybrid",
                                    json={"screenshot_ids": selected_ids, "max_patterns": 3},
                                    timeout=60
                                )
                                if hybrid_response.status_code == 200:
                                    idea = hybrid_response.json()
                                    st.session_state.hybrid_idea = idea
                                    hybrid_by_job = st.session_state.get("hybrid_idea_by_job", {})
                                    hybrid_by_job[job_id] = idea
                                    st.session_state.hybrid_idea_by_job = hybrid_by_job
                                else:
                                    st.error(f"Hybrid generation failed: {hybrid_response.text}")
                            except Exception as e:
                                st.error(f"Hybrid request failed: {e}")

                    if st.session_state.get("hybrid_idea"):
                        idea = st.session_state.hybrid_idea
                        st.markdown(f"### {idea.get('name', 'Hybrid Idea')}")
                        st.write(idea.get("description", ""))
                        st.caption(f"Best for: {idea.get('best_for', '')}")
                        features = idea.get("key_features", [])
                        if features:
                            st.markdown("**Key Features**")
                            for feature in features:
                                st.write(f"- {feature}")
            
            else:
                st.error("Failed to load results")
        
        except Exception as e:
            st.error(f"Error loading results: {e}")

if __name__ == "__main__":
    main()
