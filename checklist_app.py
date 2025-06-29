import streamlit as st
from supabase import create_client, Client
from datetime import datetime

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
    # --- 데이터 로딩 ---
    @st.cache_data(ttl=60)
    def get_checklist_data():
        profiles = supabase.table('profiles').select('id, full_name').order('full_name').execute().data
        items = supabase.table('checklist_items').select('*').eq('is_active', True).execute().data
        return profiles, items

    profiles, items = get_checklist_data()

    if not profiles or not items:
        st.warning("사용자 또는 체크리스트 항목이 등록되지 않았습니다.")
        st.stop()
    
    # --- 날짜 선택 ---
    check_date = st.date_input("날짜 선택", value=datetime.today())

    # --- 아이들별 탭 생성 ---
    profile_names = [p['full_name'] for p in profiles]
    tabs = st.tabs(profile_names)

    for i, tab in enumerate(tabs):
        with tab:
            current_profile = profiles[i]
            st.header(f"📝 {current_profile['full_name']}의 체크리스트")

            # 해당 아이에게 적용될 항목 필터링
            user_items = [item for item in items if item['target_user'] in ['공통', current_profile['full_name']]]
            
            # 체크박스 상태 저장을 위한 session_state 키 생성
            if f"checks_{current_profile['id']}_{check_date}" not in st.session_state:
                st.session_state[f"checks_{current_profile['id']}_{check_date}"] = {item['id']: True for item in user_items}

            # 체크박스 표시
            for item in user_items:
                st.session_state[f"checks_{current_profile['id']}_{check_date}"][item['id']] = st.checkbox(
                    f"{item['content']} (-{item['deduction_points']}점)", 
                    value=st.session_state[f"checks_{current_profile['id']}_{check_date}"][item['id']],
                    key=f"check_{current_profile['id']}_{item['id']}_{check_date}"
                )
            
            # 점수 계산
            violated_items = [item for item in user_items if not st.session_state[f"checks_{current_profile['id']}_{check_date}"][item['id']]]
            total_deduction = sum(item['deduction_points'] for item in violated_items)
            final_score = 110 - total_deduction

            st.write("---")
            st.subheader(f"🔻 오늘의 점수: {final_score} / 110")

            # 저장 버튼
            if st.button("오늘의 점수 저장하기", key=f"save_{current_profile['id']}_{check_date}"):
                with st.spinner("저장 중..."):
                    try:
                        violated_contents = [item['content'] for item in violated_items]
                        #  upsert = True : 같은 날짜에 같은 아이의 기록이 있으면 덮어쓰기, 없으면 새로 만들기
                        supabase.table('daily_checks').upsert({
                            'user_id': current_profile['id'],
                            'check_date': str(check_date),
                            'daily_score': final_score,
                            'violated_items': violated_contents
                        }, on_conflict='user_id, check_date').execute()
                        st.success("성공적으로 저장되었습니다!")
                    except Exception as e:
                        st.error(f"저장 중 오류 발생: {e}")