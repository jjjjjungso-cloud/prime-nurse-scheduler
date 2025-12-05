import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==========================================
# 1. 기본 설정 및 데이터 정의
# ==========================================
st.set_page_config(
    page_title="프라임 간호사 순환근무 시스템", 
    layout="wide",
    page_icon="🏥"
)

st.title("🏥 프라임팀: 데이터 기반 순환근무 시스템 (Visual Ver.)")
st.markdown("""
> **System Features:**
> 1. **Visual Timeline:** 간트 차트(Gantt)를 통해 6개월 로드맵을 한눈에 파악
> 2. **Color-Coded Schedule:** 경력/신규 여부에 따른 직관적인 색상 구분
> 3. **Time-Aware Dispatch:** 현재 시점 기준 최적 인력 추천
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
# 3. 시뮬레이션 로직 (간트차트 데이터 추가)
# ==========================================
current_skills = {nurse: set(history) for nurse, history in base_history.items()}
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
            
            # 상태 구분 (시각화용)
            if ward in base_history.get(nurse, []):
                status_icon = "🟢"
                status_text = "기존경력"
                color_code = "Veteran" # 간트차트 색상 매핑용
            else:
                status_icon = "🔵"
                status_text = "신규이수"
                color_code = "New" # 간트차트 색상 매핑용

            short_group = group_name.split('(')[0].replace("Option ", "Route ")
            
            # 날짜 계산 (Start, Finish)
            period_start = PROJECT_START_DATE + timedelta(weeks=r*2)
            period_end = period_start + timedelta(weeks=2, days=-1)
            date_str = f"{period_start.strftime('%y.%m.%d')}~{period_end.strftime('%m.%d')}"
            full_period_label = f"{date_str} ({r+1}차)"
            
            schedule.append({
                "Team": team_name, 
                "Round_Num": r + 1, 
                "Period": full_period_label,
                "Start_Date": period_start, # 간트차트용 날짜 객체
                "End_Date": period_end,     # 간트차트용 날짜 객체
                "Nurse": nurse, 
                "Group": short_group, 
                "Ward": ward, 
                "Status": status_icon,
                "Type": color_code, # Veteran vs New
                "Display": f"{ward} {status_icon}"
            })
    return pd.DataFrame(schedule)

df1 = run_simulation(team_1_nurses, structure_general, "1동")
df2 = run_simulation(team_2_nurses, structure_special, "2동")
final_schedule = pd.concat([df1, df2])

# ==========================================
# 4. 화면 구성 (Visual Upgrade)
# ==========================================
tab1, tab2, tab3 = st.tabs(["🗓️ 시각화 로드맵 & 근무표", "🔥 역량 히트맵", "🚑 시점별 인력 추천"])

with tab1:
    st.subheader("1. 전체 로드맵 시각화 (Gantt Chart)")
    st.markdown("누가 언제 어떤 병동에 가는지 **타임라인**으로 확인하세요. (막대 색상: **초록=경력** / **파랑=신규**)")
    
    # [NEW] 간트 차트 생성
    fig_gantt = px.timeline(
        final_schedule, 
        x_start="Start_Date", 
        x_end="End_Date", 
        y="Nurse", 
        color="Type", # Veteran vs New 색상 구분
        text="Ward",  # 막대 위에 병동 이름 표시
        hover_data=["Group", "Period"],
        color_discrete_map={"Veteran": "#27AE60", "New": "#3498DB"}, # 초록, 파랑
        category_orders={"Nurse": all_nurses} # 간호사 이름 순서 정렬
    )
    
    fig_gantt.update_yaxes(autorange="reversed") # 위에서 아래로
    fig_gantt.update_layout(
        xaxis_title="기간 (2026년)", 
        yaxis_title="간호사",
        showlegend=True,
        legend_title_text="상태",
        height=600,
        xaxis=dict(tickformat="%m-%d") # 날짜 형식
    )
    st.plotly_chart(fig_gantt, use_container_width=True)
    
    st.divider()
    
    st.subheader("2. 상세 근무표 (Color Table)")
    
    # 데이터 피벗
    pivot_df = final_schedule.pivot(index="Nurse", columns="Period", values="Display")
    sorted_cols = sorted(pivot_df.columns, key=lambda x: int(x.split('(')[1].replace('차)', '')))
    pivot_df = pivot_df[sorted_cols]

    # [NEW] 테이블 스타일링 함수 (색칠 공부)
    def color_coding(val):
        color = 'black'
        bg_color = 'white'
        if '🟢' in str(val):
            bg_color = '#E9F7EF' # 연한 초록 배경
        elif '🔵' in str(val):
            bg_color = '#EBF5FB' # 연한 파랑 배경
        return f'background-color: {bg_color}; color: {color}'

    # 스타일 적용해서 출력
    st.dataframe(
        pivot_df.style.map(color_coding).set_properties(**{'text-align': 'center'}),
        use_container_width=True,
        height=600
    )

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

with tab3:
    st.subheader("🆘 시점 기반 스마트 인력 추천")
    col_input, col_output = st.columns([1, 2])
    
    with col_input:
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
