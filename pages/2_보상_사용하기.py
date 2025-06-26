import streamlit as st
from supabase import Client
import time

st.set_page_config(layout="wide", page_title="포인트 샵", page_icon="🛍️")

if 'supabase_client' not in st.session_state:
    st.warning("데이터베이스 연결을 위해 홈 화면을 먼저 방문해주세요.")
    st.stop()

supabase: Client = st.session_state['supabase_client']

@st.cache_data(ttl=60)
def get_data_for_shop():
    profiles = supabase.table('profiles').select('id, full_name, current_points').order('full_name').execute().data
    rewards = supabase.table('rewards').select('id, name, point_cost').eq('is_active', True).order('point_cost').execute().data
    return profiles, rewards

profiles, rewards = get_data_for_shop()

if not profiles or not rewards:
    st.error("프로필 또는 보상 정보를 불러올 수 없습니다.")
    st.stop()

st.title("🛍️ 우리 집 포인트 샵")
st.write("---")

with st.form("redeem_reward_form"):
    st.subheader("어떤 아이가 어떤 보상을 사용하나요?")

    profile_options = {p['id']: f"{p['full_name']} (보유: {p['current_points']} BP)" for p in profiles}
    selected_profile_id = st.selectbox("가족 구성원 선택:", options=list(profile_options.keys()), format_func=lambda x: profile_options[x])

    reward_options = {r['id']: f"{r['name']} ({r['point_cost']} BP 필요)" for r in rewards}
    selected_reward_id = st.selectbox("구매할 보상 아이템 선택:", options=list(reward_options.keys()), format_func=lambda x: reward_options[x])
    
    submitted = st.form_submit_button("포인트로 구매하기")

if submitted:
    with st.spinner("포인트를 사용하고 있어요..."):
        try:
            selected_profile = next((p for p in profiles if p['id'] == selected_profile_id), None)
            selected_reward = next((r for r in rewards if r['id'] == selected_reward_id), None)
            
            points_to_spend = selected_reward['point_cost']
            current_points = selected_profile['current_points']

            if current_points < points_to_spend:
                st.error(f"포인트가 부족합니다! 현재 {current_points} BP 보유 중입니다.")
            else:
                new_points = current_points - points_to_spend
                supabase.table('profiles').update({'current_points': new_points}).eq('id', selected_profile_id).execute()

                supabase.table('redemption_log').insert({
                    "user_id": selected_profile_id, "reward_id": selected_reward_id, "points_spent": points_to_spend
                }).execute()

                st.success(f"🎉 '{selected_reward['name']}' 아이템 구매 완료!")
                st.balloons()
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
