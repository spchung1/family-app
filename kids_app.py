import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- 페이지 기본 설정 ---
st.set_page_config(layout="wide", page_title="나의 성장 앨범", page_icon="🌟")

# --- Supabase 클라이언트 초기화 ---
@st.cache_resource
def init_supabase_client():
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        return None

supabase = init_supabase_client()

# --- 로그인 상태 확인 및 처리 ---
if 'user' not in st.session_state:
    st.session_state['user'] = None

# --- 로그인 화면 ---
if st.session_state['user'] is None:
    st.title("🌟 나의 성장 앨범")
    st.write("아이디(이메일)와 비밀번호를 입력하여 로그인하세요.")

    with st.form("login_form"):
        email = st.text_input("아이디 (이메일)")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인")

        if submitted:
            if not supabase:
                st.error("시스템에 문제가 발생했습니다. 관리자에게 문의하세요.")
            else:
                try:
                    user_session = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state['user'] = user_session.user
                    st.rerun() # 로그인 성공 후 페이지 새로고침
                except Exception as e:
                    st.error("아이디 또는 비밀번호가 일치하지 않습니다.")

# --- 로그인 후 메인 화면 ---
else:
    user = st.session_state['user']

    # --- 데이터 로딩 함수 ---
    @st.cache_data(ttl=30)
    def get_my_profile(user_id):
        return supabase.table('profiles').select('*').eq('id', user_id).single().execute().data

    @st.cache_data(ttl=60)
    def get_all_rewards():
        return supabase.table('rewards').select('*').eq('is_active', True).order('point_cost').execute().data

    # 내 프로필 정보 가져오기
    my_profile = get_my_profile(user.id)
    
    # 로그아웃 버튼
    if st.sidebar.button("로그아웃"):
        st.session_state['user'] = None
        st.cache_data.clear() # 캐시 지우기
        st.rerun()

    st.sidebar.header(f"안녕하세요, {my_profile.get('full_name', '')}님!")
    st.sidebar.write("당신의 노력을 응원합니다!")
    
    st.title(f"📊 {my_profile.get('full_name', '')}님의 대시보드")
    st.write("---")

    # 내 포인트 현황 보여주기
    st.header("현재 보유 포인트")
    st.metric(label="🌟 나의 포인트", value=f"{my_profile.get('current_points', 0)} BP")
    st.write("---")

    # 포인트 샵 보여주기
    st.header("🛍️ 우리 집 포인트 샵")
    st.write("포인트를 모아 아래의 멋진 보상들을 획득해보세요!")

    rewards = get_all_rewards()
    if rewards:
        # 보상 데이터를 보기 좋게 가공
        reward_df = pd.DataFrame(rewards)[['name', 'point_cost', 'description', 'category']]
        reward_df.rename(columns={
            'name': '보상 이름',
            'point_cost': '필요 포인트',
            'description': '설명',
            'category': '카테고리'
        }, inplace=True)
        st.dataframe(reward_df, use_container_width=True, hide_index=True)
    else:
        st.info("현재 구매 가능한 보상이 없습니다.")