import streamlit as st
import google.generativeai as genai
import re

# 1. API 설정
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# 2. UI 및 세션 설정
st.set_page_config(page_title="루카 리서치 센터", layout="wide")
st.title("⚖️ 루카의 노동법률 리서치&토론 센터")

# 사이드바 (팩트체크용)
with st.sidebar:
    st.header("🔍 실시간 팩트체크")
    fact_check_container = st.empty()
    engine_status = st.empty()

if "messages" not in st.session_state:
    st.session_state.messages = []

# 기존 대화 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 3. 시스템 지시어 (환각 방지 및 토론 모드)
system_rules = """
너는 대한민국 최고의 공인노무사이자 노동법 전문 변호사야.
1. [형식]: 첫 질문은 [쟁점-근거-검토-결론] 4단계로 작성하되, 추가 질문이나 토론은 형식 없이 전문가 동료처럼 자연스럽게 대화해.
2. [팩트체크]: 판례나 행정해석 번호는 100% 확실할 때만 쓰고, 모르면 절대 지어내지 말고 확인이 필요하다고 해.
"""

# 4. 질문 처리 및 2단 스위칭 (Pro -> 3 Flash)
if prompt := st.chat_input("노무 이슈를 입력하세요."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("법리 검토 중..."):
            # 과거 대화 기록 변환 (기억 유지)
            history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} 
                       for m in st.session_state.messages[:-1]]

            try:
                # 1순위: 3.1 Pro Preview
                model = genai.GenerativeModel('gemini-3.1-pro-preview', system_instruction=system_rules)
                active_engine = "Gemini 3.1 Pro"
                response = model.start_chat(history=history).send_message(prompt)
            except:
                # 2순위: 3 Flash Preview (유저 요청 반영)
                model = genai.GenerativeModel('gemini-3-flash-preview', system_instruction=system_rules)
                active_engine = "Gemini 3 Flash"
                response = model.start_chat(history=history).send_message(prompt)

            # 결과 출력
            st.caption(f"✅ {active_engine} 엔진 분석 완료")
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            engine_status.info(f"사용 엔진: {active_engine}")

            # 팩트체크 추출 및 링크 생성
            items = re.findall(r'([가-힣]+\d*과-\d+|[가-힣]+\s?\d{5}-\d+|\d{4}[가-힣]+\s?\d+)', response.text)
            with fact_check_container.container():
                if items:
                    for item in sorted(list(set(items))):
                        st.page_link(f"https://www.google.com/search?q={item}+판례", label=f"📌 {item} 확인", icon="🔍")
                else:
                    st.info("추출된 번호 없음")
