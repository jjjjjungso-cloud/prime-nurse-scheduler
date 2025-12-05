import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. 기본 설정 및 데이터 정의
# ==========================================
st.set_page_config(
    page_title="프라임 간호사 순환근무 시스템", 
    layout="wide",
    page_icon="🏥"
)

st.title("🏥 프라임팀: 자기 주도형 순환근무 시스템 (Self-Scheduling)")
st.markdown("""
> **System Features:**
> 1. **Fixed Teams:** 1동(8명) / 2동(6명) 팀 구성 확정
> 2. **Route Selection:** 간호사가 본인의 선호도에 따라 **시작 코스(Option)** 직접 선택
> 3. **Visual Tracking:** 개인별 이동 경로 시각화 및 역량 달성도 확인
""")

# --- 병동 그룹 데이터 (Option 형태) ---
structure_general = {
    "Option 1 (시작: 순환/흉부)": ["52W", "61W", "62W"], # G2
    "Option 2 (시작: 1동_7층)": ["71W", "72W"],         # G3
    "Option 3 (시작: 내과/신장)": ["101W", "102W"],     # G4
    "Option 4 (시작: 1동_9층)": ["91W", "92W"],         # G5
    "Option 5 (시작: 호흡기)": ["122W", "131W"],        # G6
    "Option 6 (시작: 소아/산과)": ["41W", "51W"],       # G1
    "Option 7 (시작: 격리/특수)": ["82W"]               # G7
}

structure_special = {
    "Option 1 (시작: 2동_저층)": ["66W", "75W", "76W"], # G8
    "Option 2 (시작: 2동_중층)": ["85W", "86W"],        # G9
    "Option 3 (시작: 2동_고층)": ["96W", "105W", "106W"],# G10
    "Option 4 (시작: 2동_특수)": ["116W", "29W"],       # G11
    "Option 5 (시작: 소아/산과)": ["41W", "51W"],       # G1
    "Option 6 (시작: 격리/특수)": ["82W"]               # G7
}

# 전체 병동 리스트 정렬
all_wards_ordered = []
seen = set()
for grp in structure_general.values(): 
    for w in grp:
        if w not in seen: all_wards_ordered.append(w); seen.add(w)
for grp in structure_special.values(): 
    for w in grp:
        if w not in seen: all_wards_ordered.append(w); seen.add(w)

# --- [FIXED] 확정된 간호사 명단 ---
team_1_nurses = ["김유진", "김한솔", "정윤정", "정하라", "기아현", "최휘영", "박소영", "고정민"] # 8명
team_2_nurses = ["엄현지", "홍현희", "박가영", "문선희", "정소영", "김민정"] # 6명
all_nurses = team_1_nurses + team_2_nurses

# 기존 이력
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
# 2. 사이드바: 간호사별 코스 선택
# ==========================================
st.sidebar.header("👩‍⚕️ 희망 코스 선택 (Self-Scheduling)")
st.sidebar.caption("아래 팀 이름을 클릭하여 명단을 펼치세요.") # 안내 문구 추가

user_choices = {}

# [수정됨] expanded=False로 설정하여 기본적으로 접혀있게 함
with st.sidebar.expander("🔵 1동 팀원 선택 (클릭하여 펼치기)", expanded=False):
    options_1 = list(structure_general.keys())
    for idx, nurse in enumerate(team_1_nurses):
        default_idx = idx % len(options_1)
        choice = st.selectbox(f"{nurse}", options_1, index=default_idx, key=nurse)
        user_choices[nurse] = options_1.index(choice)

# [수정됨] expanded=False
with st.sidebar.expander("🔴 2동 팀원 선택 (클릭하여 펼치기)", expanded=False):
    options_2 = list(structure_special.keys())
    for idx, nurse in enumerate(team_2_nurses):
        default_idx = idx % len(options_2)
        choice = st.selectbox(f"{nurse}", options_2, index=default_idx, key=nurse)
        user_choices[nurse] = options_2.index(choice)

# ==========================================
# 3. 시뮬레이션 로직
# ==========================================
current_skills = {nurse: set(history) for nurse, history in base_history.items()}

def create_option_list(structure):
    return list(structure.items())

def run_simulation(nurses, structure, team_name):
    options_list = create_option_list(structure)
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
            is_veteran = ward in base_history.get(nurse, [])
            status_icon = "🟢" if is_veteran else "🔵"
            short_group = group_name.split('(')[0].replace("Option ", "Route ")
            
            schedule.append({
                "Team": team_name,
                "Round_Num": r + 1,
                "Period": f"{r*2+1}~{(r+1)*2}주",
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
tab1, tab2 = st.tabs(["🗓️ 순환 근무표 & 이동 경로", "🔥 역량 히트맵"])

with tab1:
    st.subheader("1. 간호사별 이동 경로 시각화 (선택 보기)")
    
    col_sel, col_chart = st.columns([1, 3])
    with col_sel:
        st.info("👇 경로를 확인할 간호사를 선택하세요.")
        selected_viewers = st.multiselect(
            "간호사 선택", 
            options=all_nurses, 
            default=["김유진", "엄현지"]
        )
    
    with col_chart:
        if selected_viewers:
            filtered_data = final_schedule[final_schedule["Nurse"].isin(selected_viewers)]
            fig_route = px.line(
                filtered_data, 
                x="Period", y="Group", color="Nurse", 
                markers=True, text="Ward", height=400,
                title="선택한 간호사의 순환 트랙"
            )
            fig_route.update_traces(textposition="top center")
            st.plotly_chart(fig_route, use_container_width=True)
        else:
            st.warning("왼쪽에서 간호사를 선택하면 이동 경로 그래프가 나타납니다.")

    st.divider()
    
    st.subheader("2. 전체 순환 근무표 (Time Table)")
    
    st.markdown("""
    <div style="background-color:#f0f2f6; padding:10px; border-radius:5px; margin-bottom:10px;">
        <b>💡 상태 아이콘 설명:</b> &nbsp;&nbsp; 
        🟢 <b>초록색:</b> 기존 경력자 (OT 불필요 / 즉시 투입) &nbsp;&nbsp;|&nbsp;&nbsp; 
        🔵 <b>파란색:</b> 신규 순환 (OT 및 교육 진행)
    </div>
    """, unsafe_allow_html=True)
    
    pivot_df = final_schedule.pivot(index="Nurse", columns="Period", values="Display")
    sorted_cols = sorted(pivot_df.columns, key=lambda x: int(x.split('~')[0]))
    pivot_df = pivot_df[sorted_cols]
    
    st.dataframe(pivot_df.style.set_properties(**{'text-align': 'center'}), use_container_width=True)

with tab2:
    st.subheader("조직 역량 커버리지 (Skill Matrix)")
    st.write("6개월 후 달성하게 될 간호사별 역량 현황입니다.")
    
    heatmap_z = []
    hover_text = []
    
    active_nurses = team_1_nurses + team_2_nurses
    
    for nurse in active_nurses:
        row = []
        txt = []
        for ward in all_wards_ordered:
            if ward in base_history.get(nurse, []): 
                row.append(1.0); txt.append("🟢 베테랑 (기존 경력)")
            elif ward in current_skills[nurse]: 
                row.append(0.5); txt.append("🔵 신규 이수 (프로젝트 성과)")
            else: 
                row.append(0.0); txt.append("미경험")
        heatmap_z.append(row); hover_text.append(txt)
        
    fig_heat = go.Figure(data=go.Heatmap(
        z=heatmap_z, x=all_wards_ordered, y=active_nurses, text=hover_text,
        hovertemplate="<b>%{y}</b> <br>병동: %{x}<br>상태: %{text}<extra></extra>",
        colorscale=[[0, "#f0f2f6"], [0.5, "#3498DB"], [1, "#27AE60"]], showscale=False, xgap=1, ygap=1
    ))
    fig_heat.update_layout(height=600, xaxis={'side':'top', 'tickangle':-45})
    st.plotly_chart(fig_heat, use_container_width=True)
