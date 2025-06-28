import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- 페이지 기본 설정 ---
st.set_page_config(layout="wide", page_title="나의 성장 앨범", page_icon="🌟")

# --- Supabase 클라이언트 초기화 ---
@st.cache_resource
def init_supabase_client():
    try:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
        SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
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
                    st.rerun()
                except Exception as e:
                    st.error("아이디 또는 비밀번호가 일치하지 않습니다.")

# --- 로그인 후 메인 앱 ---
else:
    user = st.session_state['user']

    # --- 데이터 로딩 함수 ---
    @st.cache_data(ttl=30)
    def get_my_profile(user_id):
        return supabase.table('profiles').select('*').eq('id', user_id).single().execute().data

    # 내 프로필 정보 가져오기
    my_profile = get_my_profile(user.id)
    
    # --- 사이드바 메뉴 ---
    st.sidebar.header(f"안녕하세요, {my_profile.get('full_name', '')}님!")
    st.sidebar.write("당신의 노력을 응원합니다!")
    
    page = st.sidebar.radio("메뉴를 선택하세요", ('나의 대시보드', '나의 포인트 기록', '포인트 적립 미션', '포인트 샵'))
    
    if st.sidebar.button("로그아웃"):
        st.session_state['user'] = None
        st.cache_data.clear()
        st.rerun()

    # --- 페이지별 내용 표시 ---
    if page == '나의 대시보드':
        st.title(f"📊 {my_profile.get('full_name', '')}님의 대시보드")
        st.write("---")
        st.header("현재 보유 포인트")
        st.metric(label="🌟 나의 포인트", value=f"{my_profile.get('current_points', 0)} BP")
        st.info("왼쪽 메뉴에서 다른 기능들을 확인해보세요!")

    elif page == '나의 포인트 기록':
        st.title("🧾 나의 포인트 기록")
        st.write("내가 언제 포인트를 얻고 사용했는지 모든 기록을 볼 수 있어요.")
        
        @st.cache_data(ttl=30)
        def get_my_logs(user_id):
            mission_logs_data = supabase.table('mission_log').select('created_at, notes').eq('user_id', user_id).order('created_at', desc=True).execute().data
            redemption_logs_data = supabase.table('redemption_log').select('redeemed_at, points_spent, reward_id(name)').eq('user_id', user_id).order('redeemed_at', desc=True).execute().data
            return mission_logs_data, redemption_logs_data

        mission_logs, redemption_logs = get_my_logs(user.id)
        
        all_logs = []
        for log in mission_logs:
            if log.get('notes'):
                all_logs.append({"날짜": log['created_at'], "내용": log['notes'], "종류": "포인트 변경"})
        for log in redemption_logs:
            reward_name = log.get('reward_id', {}).get('name', '알 수 없는 보상')
            all_logs.append({"날짜": log['redeemed_at'], "내용": f"'{reward_name}' 구매 (-{log['points_spent']} BP)", "종류": "보상 사용"})

        if all_logs:
            df = pd.DataFrame(all_logs)
            df['날짜'] = pd.to_datetime(df['날짜']).dt.strftime('%Y년 %m월 %d일 %H:%M')
            df = df.sort_values(by="날짜", ascending=False)
            st.dataframe(df[['날짜', '종류', '내용']], use_container_width=True, hide_index=True)
        else:
            st.info("아직 포인트 기록이 없습니다.")

    elif page == '포인트 적립 미션':
        st.title("🎯 포인트 적립 미션 목록")
        st.write("아래의 미션들을 완수하고 포인트를 획득해보세요!")

        @st.cache_data(ttl=3600) # 미션 목록은 자주 바뀌지 않으니 1시간 캐시
        def get_all_missions():
            return supabase.table('missions').select('title, description, points_reward').eq('is_active', True).order('points_reward').execute().data
        
        missions = get_all_missions()
        if missions:
            df = pd.DataFrame(missions)
            df.rename(columns={'title': '미션 이름', 'description': '설명', 'points_reward': '획득 포인트'}, inplace=True)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("현재 등록된 미션이 없습니다.")

    elif page == '포인트 샵':
        st.title("🛍️ 우리 집 포인트 샵")
        st.write("포인트를 모아 아래의 멋진 보상들을 획득해보세요!")

        @st.cache_data(ttl=3600) # 보상 목록도 1시간 캐시
        def get_all_rewards():
            return supabase.table('rewards').select('name, point_cost, description', 'category').eq('is_active', True).order('point_cost').execute().data
        
        rewards = get_all_rewards()
        if rewards:
            df = pd.DataFrame(rewards)
            df.rename(columns={'name': '보상 이름', 'point_cost': '필요 포인트', 'description': '설명', 'category': '카테고리'}, inplace=True)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("현재 구매 가능한 보상이 없습니다.")