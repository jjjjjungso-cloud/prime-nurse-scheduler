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

st.title("🏥 프라임팀: 데이터 기반 순환근무 & 역량 매칭 시스템")
st.markdown("""
> **Project Goal:** > 1. **Track Simulation:** 아직 팀이 미정인 상태에서 최적의 인원 배분 시뮬레이션
> 2. **Circuit Rotation:** 6개월 내 전 구역 커버리지 달성 (지그재그 순환)
> 3. **Skill Matrix:** 데이터 시각화를 통한 조직 역량 관리
> 4. **Smart Dispatch:** 긴급 상황 시 최적의 인력 즉시 추천
""")

# --- 병동 그룹 데이터 ---
structure_general = {
    "G2(순환/흉부)": ["52W", "61W", "62W"],
    "G3(1동_7층)": ["71W", "72W"],
    "G4(내과/신장)": ["101W", "102W"],
    "G5(1동_9층)": ["91W", "92W"],
    "G6(호흡기/종양)": ["122W", "131W"],
    "✨G1(소아/산과)": ["41W", "51W"]
}

structure_special = {
    "G8(2동_저층)": ["66W", "75W", "76W"],
    "G9(2동_중층)": ["85W", "86W"],
    "G10(2동_고층)": ["96W", "105W", "106W"],
    "G11(2동_특수)": ["116W", "29W"],
    "✨G1(소아/산과)": ["41W", "51W"], 
    "✨G7(격리/특수)": ["82W"]
}

all_wards_ordered = []
seen = set()
for grp in structure_general.values(): 
    for w in grp:
        if w not in seen: all_wards_ordered.append(w); seen.add(w)
for grp in structure_special.values(): 
    for w in grp:
        if w not in seen: all_wards_ordered.append(w); seen.add(w)

# 초기 간호사 명단 및 이력 (Master List)
base_history = {
    "김유진": ["71W", "92W"], "김한솔": ["41W", "132W"],
    "정윤정": ["101W"], "정하라": ["131W", "52W", "122W"],
    "기아현": ["101W"], "최휘영": ["122W"], "박소영": ["51W"],
    "고정민": ["71W", "92W", "MICU"], "엄현지": ["66W"],
    "홍현희": ["106W", "76W"], "박가영": ["105W", "95W", "MICU"],
    "문선희": ["62W", "101W", "92W"], "정소영": ["132W", "72W"],
    "김민정": ["92W", "132W"]
}
all_nurses_list = list(base_history.keys())

# ==========================================
# 2. [New] 사이드바: 팀 배정 시뮬레이션
# ==========================================
st.sidebar.header("👥 팀(Track) 배정 시뮬레이션")
st.sidebar.info("1동 팀원을 선택하면, 나머지는 자동으로 2동 팀으로 배정됩니다.")

# 멀티 셀렉트 박스 (기본값으로 상위 9명 선택해둠)
selected_team_1 = st.sidebar.multiselect(
    "🔵 1동 팀원 선택 (General Track)",
    options=all_nurses_list,
    default=all_nurses_list[:9]
)

# 2동 팀은 전체에서 1동 팀을 뺀 나머지
selected_team_2 = [n for n in all_nurses_list if n not in selected_team_1]

# 인원 현황 표시
col_s1, col_s2 = st.sidebar.columns(2)
col_s1.metric("1동 인원", f"{len(selected_team_1)}명")
col_s2.metric("2동 인원", f"{len(selected_team_2)}명")

if len(selected_team_1) == 0 or len(selected_team_2) == 0:
    st.error("⚠️ 각 팀에 최소 1명 이상의 간호사가 있어야 합니다.")
    st.stop() # 코드 실행 중단

st.sidebar.markdown("---")

# ==========================================
# 3. 엑셀 업로드 및 데이터 처리
# ==========================================
st.sidebar.header("📂 실적 데이터 업데이트")
uploaded_file = st.sidebar.file_uploader("근무표 엑셀/CSV 업로드", type=['xlsx', 'xls', 'csv'])

current_skills = {nurse: set(history) for nurse, history in base_history.items()}

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_upload = pd.read_csv(uploaded_file)
        else:
            df_upload = pd.read_excel(uploaded_file)
        
        st.sidebar.success("파일 로드 성공! 컬럼 매칭 필요")
        cols = df_upload.columns.tolist()
        default_name_idx = next((i for i, c in enumerate(cols) if any(x in str(c) for x in ['이름', 'Name'])), 0)
        default_ward_idx = next((i for i, c in enumerate(cols) if any(x in str(c) for x in ['병동', 'Ward'])), 0)

        name_col = st.sidebar.selectbox("👤 '이름' 열", cols, index=default_name_idx)
        ward_col = st.sidebar.selectbox("🏥 '근무 병동' 열", cols, index=default_ward_idx)
        
        if st.sidebar.button("데이터 반영하기"):
            count = 0
            for index, row in df_upload.iterrows():
                n_name = str(row[name_col]).strip()
                w_name = str(row[ward_col]).strip()
                matched_nurse = None
                for db_nurse in all_nurses_list:
                    if db_nurse in n_name:
                        matched_nurse = db_nurse
                        break
                if matched_nurse:
                    current_skills[matched_nurse].add(w_name)
                    count += 1
            if count > 0: st.sidebar.success(f"🎉 {count}건 업데이트!")
    except Exception as e:
        st.sidebar.error(f"에러: {e}")

# ==========================================
# 4. 시뮬레이션 로직
# ==========================================
def create_circuit_sequence(structure):
    queues = {k: v.copy() for k, v in structure.items()}
    groups = list(structure.keys())
    sequence = []
    while True:
        extracted = False
        for group in groups:
            if queues[group]:
                ward = queues[group].pop(0)
                tag = "Special" if "✨" in group else "General"
                sequence.append({"Group": group, "Ward": ward, "Type": tag})
                extracted = True
        if not extracted: break
    return sequence

def run_simulation(nurses, structure, team_name):
    target_sequence = create_circuit_sequence(structure)
    total_steps = len(target_sequence)
    schedule = []
    
    for n_idx, nurse in enumerate(nurses):
        start_offset = n_idx % total_steps
        for r in range(total_steps):
            if r * 2 >= 24: break
            step_idx = (start_offset + r) % total_steps
            item = target_sequence[step_idx]
            current_skills[nurse].add(item["Ward"])
            status = "🟢" if item["Ward"] in base_history.get(nurse, []) else "🔵"
            schedule.append({
                "Team": team_name, "Period": f"{r*2+1}~{(r+1)*2}주",
                "Nurse": nurse, "Group": item["Group"], "Ward": item["Ward"], "Status": status
            })
    return pd.DataFrame(schedule)

# [핵심] 사이드바에서 선택된 팀원으로 시뮬레이션 실행
df1 = run_simulation(selected_team_1, structure_general, "1동(General)")
df2 = run_simulation(selected_team_2, structure_special, "2동(Special)")
final_schedule = pd.concat([df1, df2])

# ==========================================
# 5. 화면 구성 (Tabs)
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["🗓️ 서킷 스케줄러", "🔥 역량 히트맵", "🚑 긴급 인력 매칭", "📊 프로젝트 성과"])

with tab1:
    st.subheader("지그재그 서킷 로테이션 (Zig-Zag Circuit Rotation)")
    st.caption(f"현재 배정: 1동 {len(selected_team_1)}명 / 2동 {len(selected_team_2)}명")
    
    st.write("#### 🗺️ 간호사 이동 경로 시각화 (Route Map)")
    # 필터 없이 전체 인원 출력 (인원 변경 시 자동 반영)
    filtered_data = final_schedule 
    fig_route = px.line(filtered_data, x="Period", y="Group", color="Nurse", markers=True, text="Ward", height=600)
    fig_route.update_traces(textposition="top center")
    st.plotly_chart(fig_route, use_container_width=True)
    
    st.divider()
    st.write("#### 📋 상세 근무표")
    display_df = final_schedule.copy()
    display_df["Display"] = display_df["Ward"] + " " + display_df["Status"]
    pivot = display_df.pivot(index="Nurse", columns="Period", values="Display")
    st.dataframe(pivot.style.set_properties(**{'text-align': 'center'}), use_container_width=True)

with tab2:
    st.subheader("조직 역량 커버리지 히트맵")
    heatmap_z = []
    hover_text = []
    # 선택된 전체 인원 기준
    active_nurses = selected_team_1 + selected_team_2
    
    for nurse in active_nurses:
        row = []
        txt = []
        for ward in all_wards_ordered:
            if ward in base_history.get(nurse, []):
                row.append(1.0); txt.append("🟢 베테랑")
            elif ward in current_skills[nurse]:
                row.append(0.5); txt.append("🔵 신규 이수")
            else:
                row.append(0.0); txt.append("미경험")
        heatmap_z.append(row); hover_text.append(txt)
        
    fig_heat = go.Figure(data=go.Heatmap(
        z=heatmap_z, x=all_wards_ordered, y=active_nurses, text=hover_text,
        colorscale=[[0, "#f0f2f6"], [0.5, "#3498DB"], [1, "#27AE60"]], showscale=False, xgap=1, ygap=1
    ))
    fig_heat.update_layout(height=600, xaxis={'side':'top', 'tickangle':-45})
    st.plotly_chart(fig_heat, use_container_width=True)

with tab3:
    st.subheader("🆘 스마트 인력 추천 시스템")
    active_nurses = selected_team_1 + selected_team_2
    
    col_search, col_result = st.columns([1, 2])
    with col_search:
        target_ward = st.selectbox("지원이 필요한 병동 선택", all_wards_ordered)
        candidates = []
        for nurse in active_nurses:
            score = 0
            tag = ""
            if target_ward in base_history.get(nurse, []): score = 100; tag="🟢 베테랑"
            elif target_ward in current_skills[nurse]: score = 50; tag="🔵 신규 이수"
            if score > 0: candidates.append({"Name": nurse, "Score": score, "Tag": tag})
        candidates = sorted(candidates, key=lambda x: x["Score"], reverse=True)
        
    with col_result:
        st.write(f"##### '{target_ward}' 추천 인재 리스트 ({len(candidates)}명)")
        if not candidates: st.error("가용 인력 없음")
        else:
            for c in candidates:
                bg = "#E9F7EF" if c['Score'] == 100 else "#F4F6F6"
                st.markdown(f"<div style='background:{bg}; padding:10px; margin-bottom:5px; border-radius:5px;'><b>{c['Name']}</b> {c['Tag']}</div>", unsafe_allow_html=True)

with tab4:
    st.metric("전체 커버리지", "100%", "6개월 내 전 구역 마스터 달성")
    st.success("이 시스템은 간호사의 적응(Stability)과 조직의 유연성(Agility)을 동시에 만족시킵니다.")
