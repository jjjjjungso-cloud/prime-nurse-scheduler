import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. 화면 설정
st.set_page_config(page_title="프라임 간호사 순환근무", layout="wide", page_icon="🏥")
st.title("🏥 프라임팀 순환근무 & 역량 시각화 시스템")

# 2. 데이터 정의 (고정된 명단과 병동)
# 1동 팀 (8명)
team_1 = ["김유진", "김한솔", "정윤정", "정하라", "기아현", "최휘영", "박소영", "고정민"]
wards_1 = ["52W(흉부)", "61W(순환)", "71W(외과)", "101W(내과)", "91W(내과)", "122W(호흡기)", "✨41W(소아)", "✨82W(격리)"]

# 2동 팀 (6명)
team_2 = ["엄현지", "홍현희", "박가영", "문선희", "정소영", "김민정"]
wards_2 = ["66W(저층)", "85W(중층)", "96W(고층)", "116W(특수)", "✨51W(산과)", "✨82W(격리)"]

# 기존 경력 (히트맵용)
history = {
    "김유진": ["71W(외과)", "91W(내과)"], "김한솔": ["✨41W(소아)", "122W(호흡기)"],
    "정윤정": ["101W(내과)"], "정하라": ["122W(호흡기)", "52W(흉부)"],
    # ... (필요시 더 추가 가능, 없으면 빈칸)
}

# 3. 사이드바 (깔끔하게 명단만 확인)
st.sidebar.header("📋 간호사 명단 확인")
st.sidebar.success(f"🔵 1동 팀: {len(team_1)}명")
st.sidebar.write(", ".join(team_1))
st.sidebar.warning(f"🔴 2동 팀: {len(team_2)}명")
st.sidebar.write(", ".join(team_2))

# 4. 스케줄 생성 알고리즘 (지그재그 자동 배정)
def make_schedule(nurses, wards, team_name):
    data = []
    # 간호사마다 시작 병동을 다르게 설정 (분산)
    for i, nurse in enumerate(nurses):
        start_idx = i % len(wards)
        
        for week in range(12): # 12라운드 (약 6개월)
            # 지그재그 순서 계산
            current_ward_idx = (start_idx + week) % len(wards)
            ward = wards[current_ward_idx]
            
            # 상태 아이콘 (기존 경력이면 초록, 아니면 파랑)
            status = "🟢" if ward in history.get(nurse, []) else "🔵"
            
            data.append({
                "팀": team_name,
                "기간": f"{week*2+1}~{(week+1)*2}주",
                "이름": nurse,
                "병동": f"{ward} {status}"
            })
    return pd.DataFrame(data)

df1 = make_schedule(team_1, wards_1, "1동")
df2 = make_schedule(team_2, wards_2, "2동")
df_final = pd.concat([df1, df2])

# 5. 화면 출력 (탭 2개로 끝)
tab1, tab2 = st.tabs(["📅 전체 근무표", "🔥 역량 히트맵"])

with tab1:
    st.subheader("6개월 자동 순환 근무표")
    st.caption("간호사들이 겹치지 않게 병동을 '지그재그'로 순환합니다. (🟢: 경력자 / 🔵: 신규습득)")
    
    # 보기 좋게 표로 변환
    pivot = df_final.pivot(index="이름", columns="기간", values="병동")
    st.dataframe(pivot, use_container_width=True, height=600)

with tab2:
    st.subheader("6개월 후 달성되는 조직 역량 (Skill Matrix)")
    st.caption("파란색 칸이 많을수록 우리 병원의 인력 유연성이 높아집니다.")
    
    # 히트맵 데이터 만들기
    all_nurses = team_1 + team_2
    all_wards = list(set(wards_1 + wards_2)) # 병동 목록 합치기
    all_wards.sort()
    
    z_data = []
    for nurse in all_nurses:
        row = []
        for ward in all_wards:
            # 시뮬레이션 결과 해당 병동을 경험했는지 체크
            experienced = ward in df_final[df_final["이름"]==nurse]["병동"].apply(lambda x: x.split()[0]).values
            
            if ward in history.get(nurse, []): row.append(1) # 기존 경력
            elif experienced: row.append(0.5) # 신규 습득
            else: row.append(0) # 미경험
        z_data.append(row)

    # 그래프 그리기
    fig = go.Figure(data=go.Heatmap(
        z=z_data, x=all_wards, y=all_nurses,
        colorscale=[[0, "white"], [0.5, "#3498DB"], [1, "#27AE60"]],
        showscale=False
    ))
    st.plotly_chart(fig, use_container_width=True)
