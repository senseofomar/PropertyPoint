import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(page_title="PropertyPoint Gold", layout="wide")

# PROFESSIONAL CSS: High-contrast colors for visibility
st.markdown("""
    <style>
    .main { background-color: #f0f2f5; }
    .card { 
        background: white; 
        border-radius: 12px; 
        padding: 0px; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.1); 
        margin-bottom: 25px; 
        overflow: hidden;
        border: 1px solid #ddd;
    }
    .card-content { padding: 20px; color: #1a1a1a !important; } /* Hardcoded Dark Text */
    .title-text { font-size: 1.2rem; font-weight: bold; color: #111; margin-bottom: 5px; }
    .price-text { color: #d32f2f; font-size: 1.4rem; font-weight: 800; }
    .loc-text { color: #555; font-size: 0.9rem; }
    </style>
""", unsafe_allow_html=True)

conn = sqlite3.connect('real_estate.db', check_same_thread=False)

st.title("🏙️ Premium Property Marketplace")
st.markdown("### Verified Listings in Latur")

df = pd.read_sql_query("SELECT * FROM properties", conn)

# Display Grid: 3 Items per row for better visibility
for i in range(0, len(df), 3):
    cols = st.columns(3)
    for j in range(3):
        if i + j < len(df):
            row = df.iloc[i + j]
            with cols[j]:
                st.markdown(f"""
                <div class="card">
                    <img src="{row['img_url']}" style="width:100%; height:200px; object-fit:cover;">
                    <div class="card-content">
                        <div class="title-text">{row['title']}</div>
                        <div class="loc-text">📍 {row['location']} | {row['bhk']} BHK</div>
                        <p style="color:#444; font-size:0.85rem; height:40px; overflow:hidden;">{row['description']}</p>
                        <div class="price-text">₹{row['price']:,.0f}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Enquire: {row['id']}", key=f"btn_{row['id']}"):
                    st.success("Our representative will contact you shortly!")