import streamlit as st
from supabase import Client
import time

st.set_page_config(layout="wide", page_title="포인트 관리", page_icon="💸")

# --- 데이터베이스 연결 및 데이터 로딩 ---
if 'supabase_client' not in st.session_state:
    st.warning("데이터베이스 연결을 위해 홈 화면을 먼저 방문해주세요.")
    st.stop()

supabase: Client = st.session_state['supabase_client']

@st.cache_data(ttl=60)
def get_profiles():
    try:
        return supabase.table('profiles').select('id, full_name, current_points').order('full_name').execute().data
    except Exception as e:
        st.error(f"프로필 로딩 오류: {e}")
        return []

profiles = get_profiles()
if not profiles:
    st.error("프로필 정보를 불러올 수 없습니다.")
    st.stop()

st.title("💸 포인트 지급 및 차감")
st.write("---")

profile_options = {p['id']: f"{p['full_name']} (현재: {p['current_points']} BP)" for p in profiles}
profile_ids = list(profile_options.keys())

# --- [핵심 수정 부분] 마지막 선택을 기억하기 위한 로직 ---

# 1. '기억 저장소'에 마지막 선택 기록이 없으면, 첫 번째 아이를 기본값으로 설정합니다.
if 'last_selected_profile_id' not in st.session_state:
    st.session_state.last_selected_profile_id = profile_ids[0] if profile_ids else None

# 2. 마지막으로 선택했던 아이가 현재 목록에 몇 번째에 있는지 찾습니다.
try:
    default_index = profile_ids.index(st.session_state.last_selected_profile_id)
except (ValueError, IndexError):
    default_index = 0 # 혹시라도 아이가 삭제되는 등 예외 상황 발생 시 첫 번째 아이를 선택

# --- 입력 폼 생성 ---
with st.form("point_transaction_form"):
    st.subheader("누구의 포인트를 변경할까요?")
    
    # 3. selectbox를 만들 때, 위에서 찾은 '마지막 선택'을 기본으로 보여줍니다.
    selected_profile_id = st.selectbox(
        "가족 구성원 선택:", 
        options=profile_ids, 
        format_func=lambda x: profile_options[x],
        index=default_index # 이 부분이 마지막 선택을 기억하게 만듭니다.
    )
    
    # --- 이하 폼 내용은 이전과 동일 ---
    transaction_type = st.radio("작업 종류 선택:", ('지급', '차감'), horizontal=True)
    points_to_change = st.number_input("포인트 입력:", min_value=1, step=1)
    reason = st.text_input("사유 (예: '아침 운동 완료', '규칙 위반' 등):")
    submitted = st.form_submit_button("포인트 변경 실행")

# --- 폼 제출 시 로직 처리 ---
if submitted:
    # 4. 포인트 변경이 실행되면, 현재 선택한 아이를 '마지막 선택'으로 '기억 저장소'에 업데이트합니다.
    st.session_state.last_selected_profile_id = selected_profile_id

    if not reason:
        st.error("사유를 반드시 입력해주세요.")
    else:
        with st.spinner("포인트 정보를 업데이트하고 있습니다..."):
            # (이하 포인트 처리 로직은 이전과 동일합니다)
            try:
                profile_data = supabase.table('profiles').select('current_points').eq('id', selected_profile_id).single().execute().data
                current_points = profile_data['current_points']

                if transaction_type == '지급':
                    new_points = current_points + points_to_change
                    log_message = f"+{points_to_change} BP"
                else:
                    new_points = current_points - points_to_change
                    if new_points < 0:
                        st.error(f"포인트가 부족하여 차감할 수 없습니다.")
                        st.stop()
                    log_message = f"-{points_to_change} BP"

                supabase.table('mission_log').insert({
                    "user_id": selected_profile_id, "mission_id": None, "notes": f"[{transaction_type}] {reason} ({log_message})"
                }).execute()
                
                supabase.table('profiles').update({'current_points': new_points}).eq('id', selected_profile_id).execute()

                st.success(f"✅ {profile_options[selected_profile_id].split(' (')[0]}의 포인트가 성공적으로 변경되었습니다! (현재: {new_points} BP)")
                st.balloons()
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()

            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")