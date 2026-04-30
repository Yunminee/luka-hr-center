import streamlit as st
import google.generativeai as genai
import re

# 1. API 설정
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# 2. UI 및 세션 설정
st.set_page_config(page_title="루카 리서치 센터", layout="wide")
st.title("⚖️ 루카의 노동법률 리서치 센터")

with st.sidebar:
    st.header("🔍 실시간 팩트체크")
    fact_check_container = st.empty()
    engine_status = st.empty()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 3. 강화된 시스템 지시어 (출처 표기 및 환각 방지)
system_rules = """
당신은 대한민국 최고의 공인노무사이자 법률 리서치 전문가입니다.
1. [구글 검색 필수]: 답변을 작성하기 전 반드시 구글 검색 도구를 사용하여 최신 판례, 행정해석, 법령을 확인하십시오.
2. [출처 표기 강제]: 모든 답변의 근거가 된 웹페이지나 자료는 문장 끝에 [1], [2]와 같은 주석을 달고, 답변 하단에 '참고 자료' 섹션을 만들어 해당 번호의 정확한 제목과 URL 링크를 반드시 목록 형식으로 표기하십시오.
3. [형식]: 첫 질문은 [쟁점-근거-검토-결론] 4단계로 작성하되, 추가 토론은 자연스럽게 진행하십시오.
4. [환각 금지]: 검색 결과에 없는 정보를 지어내거나 가짜 판례 번호를 생성하는 행위는 절대 금지됩니다. 모를 경우 반드시 검색 결과에 한계가 있음을 명시하십시오.
"""

# 4. 질문 처리 (검색 그라운딩 도구 장착)
if prompt := st.chat_input("확인이 필요한 노무 이슈를 입력해봐, 윤민아!"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("실시간 구글 검색 및 법리 검토 중..."):
            history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} 
                       for m in st.session_state.messages[:-1]]

            # 구글 검색 도구 설정
            tools = [{"google_search_retrieval": {}}]

            try:
                # 1순위: 3.1 Pro + 검색 도구
                model = genai.GenerativeModel('gemini-3.1-pro-preview', 
                                              system_instruction=system_rules,
                                              tools=tools)
                active_engine = "3.1 Pro (검색 연동)"
                response = model.start_chat(history=history).send_message(prompt)
            except:
                # 2순위: 3 Flash + 검색 도구
                model = genai.GenerativeModel('gemini-3-flash-preview', 
                                              system_instruction=system_rules,
                                              tools=tools)
                active_engine = "3 Flash (검색 연동)"
                response = model.start_chat(history=history).send_message(prompt)

            # 결과 출력
            st.caption(f"✅ {active_engine} 엔진 분석 완료")
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            engine_status.info(f"사용 엔진: {active_engine}")

            # 사이드바 팩트체크 링크 자동 추출 (기존 로직 유지)
            items = re.findall(r'([가-힣]+\d*과-\d+|[가-힣]+\s?\d{5}-\d+|\d{4}[가-힣]+\s?\d+)', response.text)
            with fact_check_container.container():
                if items:
                    for item in sorted(list(set(items))):
                        st.page_link(f"https://www.google.com/search?q={item}", label=f"📌 {item} 확인", icon="🔍")
                else:
                    st.info("검색된 특정 번호가 없어.")
