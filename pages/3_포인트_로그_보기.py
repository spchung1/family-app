import streamlit as st
from supabase import Client
import pandas as pd

# 페이지 기본 설정
st.set_page_config(layout="wide", page_title="포인트 기록", page_icon="🧾")

# Supabase 클라이언트 연결 가져오기
if 'supabase_client' in st.session_state:
    supabase: Client = st.session_state['supabase_client']
else:
    st.warning("데이터베이스 연결을 위해 홈 화면을 먼저 방문해주세요.")
    st.stop()

st.title("🧾 포인트 적립/사용 기록 보기")
st.write("---")

# 데이터 로딩 함수
@st.cache_data(ttl=30)
def get_logs():
    try:
        profiles_data = supabase.table('profiles').select('id, full_name').execute().data
        
        # mission_log에서는 created_at 컬럼을 사용
        mission_logs_data = supabase.table('mission_log').select('user_id, created_at, notes').order('created_at', desc=True).limit(100).execute().data
        
        # --- [중요!] 여기서 에러가 발생한 부분을 수정했습니다. 'created_at' -> 'redeemed_at' ---
        redemption_logs_data = supabase.table('redemption_log').select('user_id, redeemed_at, points_spent, reward_id').order('redeemed_at', desc=True).limit(100).execute().data
        
        rewards_data = supabase.table('rewards').select('id, name').execute().data
        
        return profiles_data, mission_logs_data, redemption_logs_data, rewards_data
    except Exception as e:
        st.error(f"로그 데이터를 불러오는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
        st.exception(e) # 개발자를 위한 자세한 에러 정보 표시
        return [], [], [], []

# 데이터 불러오기
profiles, mission_logs, redemption_logs, rewards = get_logs()

# 새로고침 버튼
if st.button("기록 새로고침"):
    st.cache_data.clear()
    st.rerun()

# 데이터를 사용하기 쉽게 가공 (매핑)
profile_map = {p['id']: p['full_name'] for p in profiles} if profiles else {}
reward_map = {r['id']: r['name'] for r in rewards} if rewards else {}

# 모든 로그를 하나의 리스트로 합치기
all_logs = []

# 미션 로그 처리
if mission_logs:
    for log in mission_logs:
        if log.get('notes'): # notes가 있는 로그만 (수동 지급/차감)
            all_logs.append({
                "날짜": log['created_at'],
                "이름": profile_map.get(log['user_id'], '알 수 없음'),
                "내용": log['notes'],
                "종류": "포인트 변경"
            })

# 보상 사용 로그 처리
if redemption_logs:
    for log in redemption_logs:
        # --- [중요!] 여기서도 에러가 발생한 부분을 함께 수정했습니다. 'created_at' -> 'redeemed_at' ---
        all_logs.append({
            "날짜": log['redeemed_at'],
            "이름": profile_map.get(log['user_id'], '알 수 없음'),
            "내용": f"'{reward_map.get(log['reward_id'], '알 수 없는 보상')}' 구매 (-{log['points_spent']} BP)",
            "종류": "보상 사용"
        })

# 최종적으로 화면에 보여주기
if all_logs:
    # 데이터프레임으로 변환
    df = pd.DataFrame(all_logs)
    
    # 날짜 순으로 다시 한번 정렬
    df['날짜'] = pd.to_datetime(df['날짜'])
    df = df.sort_values(by="날짜", ascending=False)
    
    # 날짜 형식 변경 (보기 좋게)
    df['날짜'] = df['날짜'].dt.strftime('%Y년 %m월 %d일 %H:%M')

    # 화면에 표 그리기
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("아직 포인트 기록이 없습니다.")
