import streamlit as st
from supabase import create_client, Client
import pandas as pd

# 페이지 기본 설정
st.set_page_config(layout="wide", page_title="우리 가족 포인트 시스템", page_icon="🏦")

# Supabase 클라이언트 초기화 함수
@st.cache_resource
def init_supabase_client():
    SUPABASE_URL = "https://bxvccfliphpzbvxuomqh.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ4dmNjZmxpcGhwemJ2eHVvbXFoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTA5MDI2MTksImV4cCI6MjA2NjQ3ODYxOX0.0JTcQtBBZc28493lbucMvbaN4Ptw_k1BpjnEl6CfvHk"
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"DB 연결 실패: {e}")
        return None

supabase = init_supabase_client()

if supabase:
    st.session_state['supabase_client'] = supabase

# 프로필 정보 가져오는 함수
@st.cache_data(ttl=30)
def get_all_profiles():
    if 'supabase_client' not in st.session_state: return []
    try:
        return st.session_state.supabase_client.table('profiles').select('id, full_name, current_points').order('full_name').execute().data
    except:
        return []

# --- 화면 그리기 ---
st.title("🏦 우리 가족 포인트 은행")
st.write("---")

if 'supabase_client' not in st.session_state:
    st.error("데이터베이스에 연결할 수 없습니다.")
else:
    if st.button("✨ 현황 새로고침"):
        st.cache_data.clear()
        st.rerun()

    profiles = get_all_profiles()

    if profiles:
        st.header("✨ 가족 구성원 포인트 현황")
        cols = st.columns(len(profiles))
        for i, profile in enumerate(profiles):
            with cols[i]:
                st.metric(label=f"👤 {profile['full_name']}", value=f"{profile['current_points']} BP")
    else:
        st.warning("등록된 프로필 정보가 없습니다.")

st.info("왼쪽 사이드바 메뉴를 열어 포인트를 관리하세요.")