import streamlit as st
from supabase import Client
import time

st.set_page_config(layout="wide", page_title="포인트 관리", page_icon="💸")

if 'supabase_client' not in st.session_state:
    st.warning("데이터베이스 연결을 위해 홈 화면을 먼저 방문해주세요.")
    st.stop()

supabase: Client = st.session_state['supabase_client']

@st.cache_data(ttl=60)
def get_form_data():
    try:
        profiles = supabase.table('profiles').select('id, full_name, current_points').order('full_name').execute().data
        missions = supabase.table('missions').select('id, title, points_reward').eq('is_active', True).execute().data
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

profile_options = {p['id']: f"{p['full_name']} (현재: {p['current_points']} BP)" for p in profiles}

# --- 입력 방식 선택 ---
input_method = st.radio("입력 방식을 선택하세요:", ('정해진 임무 목록에서 선택', '직접 사유 입력하기'), horizontal=True)

# --- 폼 생성 ---
with st.form("point_transaction_form"):
    st.subheader("누구의 포인트를 변경할까요?")
    
    selected_profile_id = st.selectbox("가족 구성원 선택:", options=list(profile_options.keys()), format_func=lambda x: profile_options[x])
    transaction_type = st.radio("작업 종류 선택:", ('지급', '차감'))

    # 입력 방식에 따라 다른 UI 표시
    if input_method == '정해진 임무 목록에서 선택':
        mission_options = {m['id']: f"{m['title']} (+{m['points_reward']} BP)" for m in missions}
        if not mission_options:
            st.warning("등록된 임무가 없습니다. '직접 사유 입력하기'를 이용해주세요.")
            selected_mission_id = None
        else:
            selected_mission_id = st.selectbox("완료한 임무 선택:", options=list(mission_options.keys()), format_func=lambda x: mission_options[x])
        points_to_change = None # 임무 선택 시 포인트는 자동으로 결정
        reason = None
    
    else: # 직접 사유 입력하기
        selected_mission_id = None
        points_to_change = st.number_input("포인트 입력:", min_value=1, step=1)
        reason = st.text_input("사유 (예: '동생에게 친절하게 말하기', '약속 시간 어김' 등):")

    submitted = st.form_submit_button("포인트 변경 실행")


# --- 폼 제출 시 로직 처리 ---
if submitted:
    # 유효성 검사
    if input_method == '직접 사유 입력하기' and not reason:
        st.error("사유를 반드시 입력해주세요.")
    elif input_method == '정해진 임무 목록에서 선택' and not selected_mission_id:
        st.error("선택할 임무가 없습니다. '직접 사유 입력하기'로 변경 후 다시 시도해주세요.")
    else:
        with st.spinner("포인트 정보를 업데이트하고 있습니다..."):
            try:
                # 포인트와 사유 결정
                if selected_mission_id: # 임무 선택 시
                    selected_mission = next((m for m in missions if m['id'] == selected_mission_id), None)
                    points_value = selected_mission['points_reward']
                    log_reason = selected_mission['title']
                    # 임무 선택 시에는 '지급'만 가능하도록 강제
                    if transaction_type == '차감':
                         st.error("임무 선택 시에는 '지급'만 가능합니다. '직접 사유 입력하기'로 변경하여 차감해주세요.")
                         st.stop()
                else: # 직접 입력 시
                    points_value = points_to_change
                    log_reason = reason

                # 현재 포인트 가져오기 및 계산
                profile_data = supabase.table('profiles').select('current_points').eq('id', selected_profile_id).single().execute().data
                current_points = profile_data['current_points']

                if transaction_type == '지급':
                    new_points = current_points + points_value
                    log_message = f"+{points_value} BP"
                else: # 차감
                    new_points = current_points - points_value
                    if new_points < 0:
                        st.error(f"포인트가 부족({current_points} BP)하여 차감할 수 없습니다.")
                        st.stop()
                    log_message = f"-{points_value} BP"
                
                # 로그 기록
                supabase.table('mission_log').insert({
                    "user_id": selected_profile_id,
                    "mission_id": selected_mission_id, # 임무 선택 시 ID 기록, 직접 입력 시 None
                    "notes": f"[{transaction_type}] {log_reason} ({log_message})"
                }).execute()

                # 프로필 포인트 업데이트
                supabase.table('profiles').update({'current_points': new_points}).eq('id', selected_profile_id).execute()

                st.success(f"✅ {profile_options[selected_profile_id].split(' (')[0]}의 포인트가 성공적으로 변경되었습니다! (현재: {new_points} BP)")
                st.balloons()
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()

            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
