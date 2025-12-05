import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta # 날짜 계산을 위한 도구 추가

# ==========================================
# 1. 기본 설정 및 데이터 정의
# ==========================================
st.set_page_config(
    page_title="프라임 간호사 순환근무 시스템", 
    layout="wide",
    page_icon="🏥"
)

st.title("🏥 프라임팀: 데이터 기반 순환근무 시스템 (2026 Ver.)")
st.markdown("""
> **System Features:**
> 1. **Real-Time Dates:** 2026.01.01 시작일 기준, 실제 날짜 자동 계산 표시
> 2. **Fixed Teams:** 1동(8명) / 2동(6명) 팀 구성 확정
> 3. **Route Selection:** 간호사가 본인의 선호도에 따라 시작 코스 직접 선택
""")

# --- 병동 그룹 데이터 ---
structure_general = {
    "Option 1 (시작: 순환/흉부)": ["52W", "61W", "62W"],
    "Option 2 (시작: 1동_7층)": ["71W", "72W"],
    "Option 3 (시작: 내과/신장)": ["101W", "102W"],
    "Option 4 (시작: 1동_9층)": ["91W", "92W"],
    "Option 5 (시작: 호흡기)": ["122W", "131W"],
    "Option 6 (시작: 소아/산과)": ["41W", "51W"],
    "Option 7 (시작: 격리/특수)": ["82W"]
}

structure_special = {
    "Option 1 (시작: 2동_저층)": ["66W", "75W", "76W"],
    "Option 2 (시작: 2동_중층)": ["85W", "86W"],
    "Option 3 (시작: 2동_고층)": ["96W", "105W", "106W"],
    "Option 4 (시작: 2동_특수)": ["116W", "29W"],
    "Option 5 (시작: 소아/산과)": ["41W", "51W"],
    "Option 6 (시작: 격리/특수)": ["82W"]
}

all_wards_ordered = []
seen = set()
for grp in structure_general.values(): 
    for w in grp:
        if w not in seen: all_wards_ordered.append(w); seen.add(w)
for grp in structure_special.values(): 
    for w in grp:
        if w not in seen: all_wards_ordered.append(w); seen.add(w)

team_1_nurses = ["김유진", "김한솔", "정윤정", "정하라", "기아현", "최휘영", "박소영", "고정민"]
team_2_nurses = ["엄현지", "홍현희", "박가영", "문선희", "정소영", "김민정"]
all_nurses = team_1_nurses + team_2_nurses

base_history = {
    "김유진": ["71W", "92W"], "김한솔": ["41W", "132W"],
    "정윤정": ["101W"], "정하라": ["131W", "52W", "122W"],
    "기아현": ["101W"], "최휘영": ["122W"], "박소영": ["51W"],
    "고정민": ["71W", "92W", "MICU"], "엄현지": ["66W"],
    "홍현희": ["106W", "76W"], "박가영": ["105W", "95W", "MICU"],
    "문선희": ["62W", "101W", "92W"], "정소영": ["132W", "72W"],
    "김민정": ["92W", "132W"]
}

# ==========================================
# 2. 사이드바: 선택 시스템
# ==========================================
st.sidebar.header("👩‍⚕️ 희망 코스 선택")
user_choices = {}

with st.sidebar.expander("🔵 1동 팀원 선택 (클릭)", expanded=False):
    options_1 = list(structure_general.keys())
    for idx, nurse in enumerate(team_1_nurses):
        default_idx = idx % len(options_1)
        choice = st.selectbox(f"{nurse}", options_1, index=default_idx, key=nurse)
        user_choices[nurse] = options_1.index(choice)

with st.sidebar.expander("🔴 2동 팀원 선택 (클릭)", expanded=False):
    options_2 = list(structure_special.keys())
    for idx, nurse in enumerate(team_2_nurses):
        default_idx = idx % len(options_2)
        choice = st.selectbox(f"{nurse}", options_2, index=default_idx, key=nurse)
        user_choices[nurse] = options_2.index(choice)

# ==========================================
# 3. 시뮬레이션 로직 (날짜 계산 추가)
# ==========================================
current_skills = {nurse: set(history) for nurse, history in base_history.items()}

# [New] 프로젝트 시작일 설정
PROJECT_START_DATE = datetime(2026, 1, 1)

def run_simulation(nurses, structure, team_name):
    options_list = list(structure.items())
    total_steps = len(options_list)
    schedule = []
    
    for nurse in nurses:
        start_offset = user_choices.get(nurse, 0)
        for r in range(total_steps):
            if r * 2 >= 24: break
            step_idx = (start_offset + r) % total_steps
            group_name, wards = options_list[step_idx]
            ward = wards[0] 
            
            current_skills[nurse].add(ward)
            status_icon = "🟢" if ward in base_history.get(nurse, []) else "🔵"
            short_group = group_name.split('(')[0].replace("Option ", "Route ")
            
            # [New] 날짜 계산 로직
            # 1라운드당 2주(14일)씩 더함
            period_start = PROJECT_START_DATE + timedelta(weeks=r*2)
            # 2주 뒤에서 하루 뺌 (예: 1일~14일)
            period_end = period_start + timedelta(weeks=2, days=-1)
            
            # 문자열 포맷팅 (예: 26.01.01 ~ 01.14 (1차))
            date_str = f"{period_start.strftime('%y.%m.%d')} ~ {period_end.strftime('%m.%d')}"
            full_period_label = f"{date_str} ({r+1}차)"
            
            schedule.append({
                "Team": team_name, 
                "Round_Num": r + 1, 
                "Period": full_period_label, # 날짜가 포함된 라벨 사용
                "Nurse": nurse, 
                "Group": short_group, 
                "Ward": ward, 
                "Status": status_icon,
                "Display": f"{ward} {status_icon}"
            })
    return pd.DataFrame(schedule)

df1 = run_simulation(team_1_nurses, structure_general, "1동")
df2 = run_simulation(team_2_nurses, structure_special, "2동")
final_schedule = pd.concat([df1, df2])

# ==========================================
# 4. 화면 구성
# ==========================================
tab1, tab2, tab3 = st.tabs(["🗓️ 순환 근무표", "🔥 전체 역량 히트맵", "🚑 시점별 인력 추천"])

with tab1:
    st.subheader("1. 간호사별 이동 경로 시각화")
    col_sel, col_chart = st.columns([1, 3])
    with col_sel:
        st.info("👇 경로를 확인할 간호사를 선택하세요.")
        selected_viewers = st.multiselect("간호사 선택", options=all_nurses, default=["김유진", "엄현지"])
    with col_chart:
        if selected_viewers:
            filtered_data = final_schedule[final_schedule["Nurse"].isin(selected_viewers)]
            fig_route = px.line(filtered_data, x="Period", y="Group", color="Nurse", markers=True, text="Ward", height=400)
            fig_route.update_traces(textposition="top center")
            st.plotly_chart(fig_route, use_container_width=True)
    
    st.divider()
    st.subheader("2. 전체 순환 근무표 (2026년 상반기)")
    st.markdown("""
    <div style="background-color:#f0f2f6; padding:10px; border-radius:5px; margin-bottom:10px; color:black;">
        <b>💡 상태 아이콘 설명:</b> &nbsp;&nbsp; 
        🟢 <b>초록색:</b> 기존 경력자 (OT 불필요) &nbsp;&nbsp;|&nbsp;&nbsp; 
        🔵 <b>파란색:</b> 신규 순환 (교육 필요)
    </div>
    """, unsafe_allow_html=True)

    pivot_df = final_schedule.pivot(index="Nurse", columns="Period", values="Display")
    
    # [Fix] 날짜순 정렬 (Round_Num을 기준으로 정렬하기 위해 다시 매핑)
    # Period 문자열 안에 있는 "(1차)", "(2차)" 등의 숫자를 읽어서 정렬
    sorted_cols = sorted(pivot_df.columns, key=lambda x: int(x.split('(')[1].replace('차)', '')))
    
    st.dataframe(pivot_df[sorted_cols].style.set_properties(**{'text-align': 'center'}), use_container_width=True)

with tab2:
    st.subheader("최종 완료 시점(2026년 6월) 역량 히트맵")
    heatmap_z = []
    hover_text = []
    for nurse in all_nurses:
        row = []
        txt = []
        for ward in all_wards_ordered:
            if ward in base_history.get(nurse, []): row.append(1.0); txt.append("🟢 베테랑")
            elif ward in current_skills[nurse]: row.append(0.5); txt.append("🔵 신규 이수")
            else: row.append(0.0); txt.append("미경험")
        heatmap_z.append(row); hover_text.append(txt)
    fig_heat = go.Figure(data=go.Heatmap(
        z=heatmap_z, x=all_wards_ordered, y=all_nurses, text=hover_text,
        colorscale=[[0, "#f0f2f6"], [0.5, "#3498DB"], [1, "#27AE60"]], showscale=False, xgap=1, ygap=1
    ))
    fig_heat.update_layout(height=600, xaxis={'side':'top', 'tickangle':-45})
    st.plotly_chart(fig_heat, use_container_width=True)

# ---------------------------------------------------------
# TAB 3: 시점 기반 인력 추천 (날짜 슬라이더 적용)
# ---------------------------------------------------------
with tab3:
    st.subheader("🆘 시점 기반 스마트 인력 추천")
    st.markdown("현재 날짜(기간)를 선택하면, **해당 시점까지 교육을 완료한** 인력만 추천합니다.")
    
    col_input, col_output = st.columns([1, 2])
    
    with col_input:
        # 날짜가 포함된 기간 목록 생성
        periods = sorted(final_schedule['Period'].unique(), key=lambda x: int(x.split('(')[1].replace('차)', '')))
        current_period = st.select_slider("⏳ 현재 날짜 선택", options=periods, value=periods[0])
        
        target_ward = st.selectbox("🚑 지원이 필요한 병동", all_wards_ordered)
        
        current_round_idx = periods.index(current_period)
        valid_periods = periods[:current_round_idx+1]
        valid_history_df = final_schedule[final_schedule['Period'].isin(valid_periods)]
        
        candidates = []
        for nurse in all_nurses:
            score = 0; tag = ""; desc = ""
            
            if target_ward in base_history.get(nurse, []):
                score = 100; tag = "🟢 베테랑"; desc = "기존 경력 보유 (즉시 투입)"
            else:
                visited_wards = valid_history_df[valid_history_df['Nurse'] == nurse]['Ward'].unique()
                if target_ward in visited_wards:
                    score = 50; tag = "🔵 교육 이수"
                    when = valid_history_df[(valid_history_df['Nurse'] == nurse) & (valid_history_df['Ward'] == target_ward)]['Period'].values[0]
                    # 날짜만 깔끔하게 추출해서 보여줌
                    simple_date = when.split(' (')[0]
                    desc = f"{simple_date} 기간에 근무 완료"
            
            if score > 0: candidates.append({"Name": nurse, "Score": score, "Tag": tag, "Desc": desc})
        candidates = sorted(candidates, key=lambda x: x["Score"], reverse=True)

    with col_output:
        st.write(f"### 📋 '{current_period.split('(')[0]}' 기준 가용 인력: {len(candidates)}명")
        
        if not candidates:
            st.warning(f"⚠️ 이 시점에는 아직 '{target_ward}' 경험자가 없습니다.")
        else:
            for c in candidates:
                bg = "#E9F7EF" if c['Score'] == 100 else "#D6EAF8"
                st.markdown(f"""
                <div style="background-color:{bg}; padding:15px; margin-bottom:10px; border-radius:10px; border:1px solid #ccc;">
                    <span style="font-size:1.2em; font-weight:bold; color:black;">{c['Name']}</span> 
                    <span style="float:right; font-weight:bold; color:black;">{c['Tag']}</span>
                    <br>
                    <span style="font-size:0.9em; color:#333;">💡 {c['Desc']}</span>
                </div>
                """, unsafe_allow_html=True)
