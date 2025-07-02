import streamlit as st
from supabase import Client
import time

st.set_page_config(layout="wide", page_title="포인트 관리", page_icon="💸")

# --- 데이터베이스 연결 및 데이터 로딩 ---
if 'supabase_client' not in st.session_state:
    st.warning("데이터베이스 연결을 위해 홈 화면을 먼저 방문해주세요.", icon="🏠")
    st.stop()

supabase: Client = st.session_state['supabase_client']

@st.cache_data(ttl=60)
def get_form_data():
    try:
        profiles = supabase.table('profiles').select('id, full_name, current_points').order('full_name').execute().data
        missions = supabase.table('missions').select('id, title, points_reward').order('title').execute().data
        return profiles, missions
    except Exception as e:
        st.error(f"데이터 로딩 오류: {e}")
        return [], []

profiles, missions = get_form_data()
if not profiles:
    st.error("프로필 정보를 불러올 수 없습니다.")
    st.stop()

st.title("💸 포인트 지급 및 차감")
st.write("---")

# --- [핵심 수정] 마지막 선택 기억 및 입력 방식 선택 UI ---

# 1. '기억 저장소' 초기화
if 'last_selected_profile_id' not in st.session_state:
    st.session_state.last_selected_profile_id = profiles[0]['id'] if profiles else None

# 2. 마지막 선택했던 아이의 인덱스 찾기
try:
    profile_ids = [p['id'] for p in profiles]
    default_index = profile_ids.index(st.session_state.last_selected_profile_id)
except (ValueError, IndexError):
    default_index = 0

# --- 입력 폼 생성 ---
with st.form("point_transaction_form"):
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. 누구의 포인트를 변경할까요?")
        selected_profile_id = st.selectbox(
            "가족 구성원 선택:", 
            options=profile_ids, 
            format_func=lambda x: f"{next(p['full_name'] for p in profiles if p['id'] == x)} (현재: {next(p['current_points'] for p in profiles if p['id'] == x)} BP)",
            index=default_index,
            label_visibility="collapsed"
        )
    
    with col2:
        st.subheader("2. 어떤 방식으로 지급할까요?")
        input_method = st.radio(
            "입력 방식 선택:", 
            ('정해진 임무 목록에서 선택', '직접 사유 입력하기'), 
            horizontal=True,
            label_visibility="collapsed"
        )

    st.write("---")
    st.subheader("3. 내용 입력")

    # 입력 방식에 따라 다른 UI 표시
    if input_method == '정해진 임무 목록에서 선택':
        mission_options = {m['id']: f"{m['title']} (+{m['points_reward']} BP)" for m in missions}
        if not mission_options:
            st.warning("등록된 임무가 없습니다. '직접 사유 입력하기'를 이용해주세요.")
            selected_mission_id = None
        else:
            selected_mission_id = st.selectbox("완료한 임무 선택:", options=list(mission_options.keys()), format_func=lambda x: mission_options[x])
        # 임무 선택 시, 포인트와 사유는 자동으로 결정되므로 입력칸을 비활성화
        points_to_change = 0
        reason = ""
        transaction_type = "지급"

    else: # 직접 사유 입력하기
        selected_mission_id = None
        transaction_type = st.radio("작업 종류 선택:", ('지급', '차감'))
        points_to_change = st.number_input("포인트 입력:", min_value=1, step=1)
        reason = st.text_input("사유 (예: '동생에게 친절하게 말함', '약속 시간 어김' 등):")

    submitted = st.form_submit_button("포인트 변경 실행")


# --- 폼 제출 시 로직 처리 ---
if submitted:
    st.session_state.last_selected_profile_id = selected_profile_id

    if input_method == '직접 사유 입력하기' and not reason:
        st.error("사유를 반드시 입력해주세요.")
    elif input_method == '정해진 임무 목록에서 선택' and not selected_mission_id: