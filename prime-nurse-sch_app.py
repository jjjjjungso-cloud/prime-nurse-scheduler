import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. 기본 설정 및 데이터 정의
# ==========================================
st.set_page_config(
    page_title="프라임 간호사 통합 시스템", 
    layout="wide",
    page_icon="🏥"
)

st.title("🏥 프라임팀: 자기 주도형 순환근무 시스템 (Self-Scheduling)")
st.markdown("""
> **Project Goal:** > 1. **Choice-Based:** 간호사가 본인의 선호도에 따라 **순환 코스(Option)**를 직접 선택
> 2. **Circuit Rotation:** 선택한 시작점부터 지그재그로 전 구역 순환
> 3. **Full Mastery:** 6개월 내 배정된 트랙의 모든 병동 경험 완료
""")

# --- 병동 그룹 데이터 ---
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

# 확정된 간호사 명단
team_1_nurses = ["김유진", "김한솔", "정윤정", "정하라", "기아현", "최휘영", "박소영", "고정민"] # 1동
team_2_nurses = ["엄현지", "홍현희", "박가영", "문선희", "정소영", "김민정"] # 2동
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
# 2. [New] 사이드바: 간호사별 선택 시스템
# ==========================================
st.sidebar.header("👩‍⚕️ 간호사 코스 선택 (Selection)")
st.sidebar.info("본인이 희망하는 '시작 그룹(Option)'을 선택하세요.")

# 선택 저장소 (Session State가 없으므로 매번 리셋되지만, 데모용으로는 충분)
# 기본값: 골고루 분산되도록 설정
user_choices = {}

with st.sidebar.expander("🔵 1동 팀원 선택 (Click to Open)", expanded=True):
    options_1 = list(structure_general.keys())
    for idx, nurse in enumerate(team_1_nurses):
        # 기본값은 인덱스 순서대로 분산
        default_idx = idx % len(options_1)
        choice = st.selectbox(f"{nurse}님의 희망 코스", options_1, index=default_idx, key=nurse)
        # 선택한 Option이 리스트에서 몇 번째인지 찾기
        user_choices[nurse] = options_1.index(choice)

with st.sidebar.expander("🔴 2동 팀원 선택 (Click to Open)", expanded=True):
    options_2 = list(structure_special.keys())
    for idx, nurse in enumerate(team_2_nurses):
        default_idx = idx % len(options_2)
        choice = st.selectbox(f"{nurse}님의 희망 코스", options_2, index=default_idx, key=nurse)
        user_choices[nurse] = options_2.index(choice)

# ==========================================
# 3. 엑셀 업로드 (기존 유지)
# ==========================================
st.sidebar.markdown("---")
st.sidebar.header("📂 실적 데이터 업데이트")
uploaded_file = st.sidebar.file_uploader("근무표 엑셀/CSV 업로드", type=['xlsx', 'xls', 'csv'])
current_skills = {nurse: set(history) for nurse, history in base_history.items()}

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'): df_upload = pd.read_csv(uploaded_file)
        else: df_upload = pd.read_excel(uploaded_file)
        cols = df_upload.columns.tolist()
        name_col = st.sidebar.selectbox("이름 열", cols)
        ward_col = st.sidebar.selectbox("병동 열", cols)
        if st.sidebar.button("반영"):
            for index, row in df_upload.iterrows():
                n = str(row[name_col]).strip()
                w = str(row[ward_col]).strip()
                for db_n in all_nurses:
                    if db_n in n: current_skills[db_n].add(w)
            st.sidebar.success("업데이트 완료")
    except: pass

# ==========================================
# 4. 시뮬레이션 로직 (선택 반영)
# ==========================================
def create_circuit_sequence(structure):
    # 구조체 자체를 리스트로 변환 (순서 유지)
    # structure의 key 자체가 "Option X" 형태임
    return list(structure.items())

def run_simulation(nurses, structure, team_name):
    # Option 리스트 (예: [('Option 1', [52W..]), ('Option 2', [71W..])...])
    options_list = create_circuit_sequence(structure)
    total_steps = len(options_list)
    schedule = []
    
    for nurse in nurses:
        # [핵심] 사용자가 선택한 Option 번호를 시작점(Offset)으로 사용
        start_offset = user_choices.get(nurse, 0)
        
        for r in range(total_steps):
            if r * 2 >= 24: break
            
            # 선택한 시작점부터 순서대로 순환
            step_idx = (start_offset + r) % total_steps
            group_name, wards = options_list[step_idx]
            
            # 병동은 큐에서 하나씩 뽑는 게 아니라, 해당 그룹의 첫 번째 병동 배정 (단순화)
            # 실제로는 그룹 내 병동도 로테이션 되지만, 여기선 그룹 선택을 강조
            ward = wards[r % len(wards)] 
            
            current_skills[nurse].add(ward)
            status = "🟢" if ward in base_history.get(nurse, []) else "🔵"
            
            # 그룹 이름에서 "Option X" 부분만 짧게 표시
            short_group = group_name.split('(')[0].strip()
            
            schedule.append({
                "Team": team_name, "Period": f"{r*2+1}~{(r+1)*2}주",
                "Nurse": nurse, "Group": short_group, "Ward": ward, "Status": status
            })
    return pd.DataFrame(schedule)

df1 = run_simulation(team_1_nurses, structure_general, "1동(General)")
df2 = run_simulation(team_2_nurses, structure_special, "2동(Special)")
final_schedule = pd.concat([df1, df2])

# ==========================================
# 5. 화면 구성
# ==========================================
tab1, tab2, tab3 = st.tabs(["🗓️ 선택형 스케줄러", "🔥 역량 히트맵", "🚑 긴급 인력 매칭"])

with tab1:
    st.subheader("내가 선택한 코스로 만드는 근무표")
    st.info("👈 왼쪽 사이드바에서 본인의 **'희망 시작 코스(Option)'**를 변경해보세요. 스케줄이 실시간으로 바뀝니다.")
    
    # 그래프
    fig_route = px.line(final_schedule, x="Period", y="Group", color="Nurse", markers=True, text="Ward", height=600)
    fig_route.update_traces(textposition="top center")
    st.plotly_chart(fig_route, use_container_width=True)
    
    # 표
    display_df = final_schedule.copy()
    display_df["Display"] = display_df["Ward"] + " " + display_df["Status"]
    pivot = display_df.pivot(index="Nurse", columns="Period", values="Display")
    st.dataframe(pivot.style.set_properties(**{'text-align': 'center'}), use_container_width=True)

with tab2:
    st.subheader("조직 역량 커버리지")
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
    st.subheader("🆘 스마트 인력 추천")
    target_ward = st.selectbox("지원이 필요한 병동", all_wards_ordered)
    candidates = []
    for nurse in all_nurses:
        score = 0; tag = ""
        if target_ward in base_history.get(nurse, []): score=100; tag="🟢 베테랑"
        elif target_ward in current_skills[nurse]: score=50; tag="🔵 신규"
        if score>0: candidates.append({"Name": nurse, "Score": score, "Tag": tag})
    candidates = sorted(candidates, key=lambda x: x["Score"], reverse=True)
    
    if candidates:
        for c in candidates:
            bg = "#E9F7EF" if c['Score']==100 else "#F4F6F6"
            st.markdown(f"<div style='background:{bg}; padding:10px; margin-bottom:5px; border-radius:5px;'><b>{c['Name']}</b> {c['Tag']}</div>", unsafe_allow_html=True)
    else: st.error("가용 인력 없음")
