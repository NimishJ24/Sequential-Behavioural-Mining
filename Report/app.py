import streamlit as st
import os
from bs4 import BeautifulSoup
import json
from openai import OpenAI
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="Employee Activity Monitor",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main {
        background-color: #f5f7ff;
    }
    .stButton>button {
        background-color: #4267B2;
        color: white;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        border: none;
    }
    .stButton>button:hover {
        background-color: #34518c;
    }
    .reportBlock {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stSidebar {
        background-color: #ffffff;
    }
    .metric-card {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)

def initialize_openai():
    try:
        api_key = os.getenv("OPENAI_API_KEY")  
        if not api_key:
            raise ValueError("API key not found in environment variables.")
        return OpenAI(api_key=api_key)
    except Exception as e:
        st.error(f"Error accessing OpenAI API key: {str(e)}")
        return None

def create_usage_chart(data):
    df = pd.DataFrame(data['visited_webpages'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df['url'],
        y=df['time_spent'],
        marker_color='#4267B2',
        name='Time Spent (seconds)'
    ))
    
    fig.update_layout(
        title="Website Usage Distribution",
        xaxis_title="Website URL",
        yaxis_title="Time Spent (seconds)",
        template="plotly_white",
        height=400
    )
    
    return fig

def create_transitions_diagram(transitions):
    nodes = set()
    for t in transitions:
        nodes.add(t['from'])
        nodes.add(t['to'])
    
    nodes = list(nodes)
    node_indices = {node: i for i, node in enumerate(nodes)}
    
    edge_x = []
    edge_y = []
    for t in transitions:
        x0 = node_indices[t['from']] * 2
        x1 = node_indices[t['to']] * 2
        edge_x.extend([x0, x1, None])
        edge_y.extend([0, 0, None])
    
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines')
    
    node_x = [i * 2 for i in range(len(nodes))]
    node_y = [0] * len(nodes)
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=nodes,
        textposition="bottom center",
        marker=dict(
            showscale=False,
            size=20,
            color='#4267B2',
        ))
    
    fig = go.Figure(data=[edge_trace, node_trace],
                   layout=go.Layout(
                       title="Page Transition Flow",
                       showlegend=False,
                       hovermode='closest',
                       margin=dict(b=20,l=5,r=5,t=40),
                       xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                       yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                       height=300
                   ))
    
    return fig

def calculate_metrics(data):
    total_time = sum(page['time_spent'] for page in data['visited_webpages'])
    work_sites = sum(1 for page in data['visited_webpages'] if 'workportal' in page['url'])
    non_work_sites = sum(1 for page in data['visited_webpages'] if 'workportal' not in page['url'])
    
    return {
        "total_time": total_time,
        "work_sites": work_sites,
        "non_work_sites": non_work_sites,
        "total_transitions": len(data['page_transitions'])
    }

def get_employee_report(data):
    openai = initialize_openai()
    if not openai:
        return None
        
    system_prompt = """
    You are an AI assistant that analyzes user behavior on a computer to generate a detailed employee activity report.  
    Analyze the provided data and generate a clear, professional report with these sections:
    1. Summary of Activity
    2. Work vs Non-work Usage Analysis
    3. Potential Security Concerns
    4. Recommendations
    
    Use markdown formatting for headers and key points.
    """
    
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze this data: {json.dumps(data)}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error generating report: {str(e)}")
        return None

def main(data):
    st.title("👥 Employee Activity Monitor")
    
   
    metrics = calculate_metrics(data)

    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total Time", f"{metrics['total_time']} sec")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Work Sites", metrics['work_sites'])
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Non-work Sites", metrics['non_work_sites'])
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Page Transitions", metrics['total_transitions'])
        st.markdown('</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Usage Statistics")
        usage_chart = create_usage_chart(data)
        st.plotly_chart(usage_chart, use_container_width=True)
    
    with col2:
        st.subheader("🔄 Page Transitions")
        transitions_chart = create_transitions_diagram(data['page_transitions'])
        st.plotly_chart(transitions_chart, use_container_width=True)
    
    if st.button("Generate Report"):
        with st.spinner("Analyzing employee activity..."):
            report = get_employee_report(data)
            if report:
                st.markdown('<div class="reportBlock">', unsafe_allow_html=True)
                st.markdown(report)
                st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
   
    data = {
        "visited_webpages": [
            {"url": "https://workportal.com/dashboard", "time_spent": 300, "timestamp": "2025-02-03T10:00:00"},
            {"url": "https://socialmedia.com", "time_spent": 120, "timestamp": "2025-02-03T10:05:00"},
            {"url": "https://workportal.com/reports", "time_spent": 600, "timestamp": "2025-02-03T10:07:00"},
            {"url": "https://shopping.com", "time_spent": 200, "timestamp": "2025-02-03T10:20:00"}
        ],
        "page_transitions": [
            {"from": "https://workportal.com/dashboard", "to": "https://socialmedia.com"},
            {"from": "https://socialmedia.com", "to": "https://workportal.com/reports"},
            {"from": "https://workportal.com/reports", "to": "https://shopping.com"}
        ]
    }
    
    main(data)
