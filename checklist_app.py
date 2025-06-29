import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import pandas as pd

# --- 페이지 기본 설정 ---
st.set_page_config(layout="wide", page_title="우리 가족 체크리스트", page_icon="✅")

# --- Supabase 클라이언트 초기화 ---
@st.cache_resource
def init_supabase_client():
    try:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
        SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"DB 연결 실패: {e}")
        return None

supabase = init_supabase_client()

st.title("✅ 우리 가족 일일 체크리스트")
st.write("---")

if not supabase:
    st.error("데이터베이스에 연결할 수 없습니다.")
else:
    # --- 데이터 로딩 함수 (수정됨) ---
    @st.cache_data(ttl=60)
    def get_checklist_data():
        try:
            profiles = supabase.table('profiles').select('id, full_name').order('full_name').execute().data
            # [수정] eq 필터에 사용된 'is_active' 컬럼을 select 목록에 추가했습니다.
            items = supabase.table('checklist_items').select('id, content, target_user, deduction_points, is_active').eq('is_active', True).execute().data
            return profiles, items
        except Exception as e:
            st.error("체크리스트 데이터를 불러오는 데 실패했습니다.")
            st.exception(e)
            return [], []

    profiles, items = get_checklist_data()

    # 데이터 로딩 실패 시 앱 중단
    if not profiles:
        st.warning("사용자 프로필 정보가 없습니다. 관리자에게 문의하세요.")
        st.stop()
    if not items:
        st.warning("체크리스트 항목이 없습니다. 관리자에게 문의하세요.")
        st.stop()
    
    # --- 날짜 선택 ---
    check_date = st.date_input("날짜 선택", value=datetime.today())

    # --- 아이들별 탭 생성 ---
    profile_map = {p['id']: p['full_name'] for p in profiles}
    tabs = st.tabs(list(profile_map.values()))

    for i, profile_id in enumerate(profile_map.keys()):
        with tabs[i]:
            full_name = profile_map[profile_id]
            st.header(f"📝 {full_name}의 체크리스트")

            user_items = [item for item in items if item['target_user'] in ['공통', full_name]]
            
            session_key = f"checks_{profile_id}_{check_date}"
            if session_key not in st.session_state:
                st.session_state[session_key] = {item['id']: True for item in user_items}

            for item in user_items:
                # 날짜가 바뀔 때 체크박스 값을 초기화하기 위한 로직
                current_value = st.session_state[session_key].get(item['id'], True)
                st.session_state[session_key][item['id']] = st.checkbox(
                    f"{item['content']} (-{item['deduction_points']}점)", 
                    value=current_value,
                    key=f"check_{profile_id}_{item['id']}_{check_date}"
                )
            
            violated_items = [item for item in user_items if not st.session_state[session_key].get(item['id'], True)]
            total_deduction = sum(item['deduction_points'] for item in violated_items)
            final_score = 110 - total_deduction

            st.write("---")
            st.subheader(f"🔻 오늘의 점수: {final_score} / 110")

            if st.button("오늘의 점수 저장하기", key=f"save_{profile_id}_{check_date}"):
                with st.spinner("저장 중..."):
                    try:
                        violated_contents = [item['content'] for item in violated_items]
                        supabase.table('daily_checks').upsert({
                            'user_id': profile_id,
                            'check_date': str(check_date),
                            'daily_score': final_score,
                            'violated_items': violated_contents
                        }, on_conflict='user_id, check_date').execute()
                        st.success(f"{full_name}의 {check_date} 기록이 성공적으로 저장되었습니다!")
                    except Exception as e:
                        st.error(f"저장 중 오류 발생: {e}")