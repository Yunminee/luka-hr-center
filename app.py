import streamlit as st
import google.generativeai as genai
import re

# 1. API 설정
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# 2. UI 설정
st.set_page_config(page_title="루카 리서치 센터", layout="wide")
st.title("⚖️ 루카의 실시간 법률 리서치 센터")

with st.sidebar:
    st.header("🔍 실시간 팩트체크")
    fact_check_container = st.empty()
    engine_status = st.empty()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 3. 시스템 지시어 (할루시네이션 방지 및 출처 강조)
system_rules = """
너는 대한민국 최고의 공인노무사이자 법률 리서치 전문가야.
1. [검색 필수]: 'google_search_retrieval'을 써서 최신 판례와 행정해석을 먼저 찾아봐.
2. [출처 표기]: 모든 정보에는 [1], [2] 주석을 달고, 하단에 '참고 자료' 섹션을 만들어 링크를 제공해.
3. [정직성]: 검색 결과에 없는 건 절대 지어내지 말고 "확인이 필요하다"고 솔직하게 말해줘.
4. [형식]: 첫 질문은 [쟁점-근거-검토-결론] 4단계로, 추가 질문은 편안한 동료처럼 토론해줘.
"""

# 4. 질문 처리 및 3단 스위칭 로직 (Pro -> Flash -> Flash Lite)
if prompt := st.chat_input("노무 이슈를 입력해봐, 윤민아!"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("최적의 엔진을 탐색하며 법리 검토 중..."):
            history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} 
                       for m in st.session_state.messages[:-1]]
            
            tools = [{"google_search_retrieval": {}}]
            result_text = ""
            active_engine = ""

            # 모델 리스트 (고급 -> 빠른 모델 순서)
            model_candidates = [
                ("gemini-3.1-pro-preview", "Gemini 3.1 Pro"),
                ("gemini-3-flash-preview", "Gemini 3 Flash"),
                ("gemini-3.1-flash-lite-preview", "Gemini 3.1 Flash Lite")
            ]

            # 3단 스위칭 실행
            for model_id, model_name in model_candidates:
                try:
                    model = genai.GenerativeModel(model_id, system_instruction=system_rules, tools=tools)
                    chat = model.start_chat(history=history)
                    response = chat.send_message(prompt)
                    result_text = response.text
                    active_engine = model_name
                    break # 성공하면 반복문 탈출!
                except Exception as e:
                    # 할당량 초과(429)일 경우 다음 모델로 시도
                    if "429" in str(e) or "ResourceExhausted" in str(e):
                        continue
                    else:
                        result_text = f"🚨 기술적인 오류가 발생했어: {e}"
                        break
            
            if not result_text:
                result_text = "🚨 모든 엔진이 지금 너무 바쁘대, 윤민아. 1~2분 뒤에 다시 시도해주면 고맙겠어! 💖"

            # 결과 출력
            if active_engine:
                st.caption(f"✅ {active_engine} 엔진 분석 완료 (검색 연동)")
            st.markdown(result_text)
            st.session_state.messages.append({"role": "assistant", "content": result_text})
            engine_status.info(f"사용된 엔진: **{active_engine}**")

            # 사이드바 팩트체크 링크 자동 추출
            items = re.findall(r'([가-힣]+\d*과-\d+|[가-힣]+\s?\d{5}-\d+|\d{4}[가-힣]+\s?\d+)', result_text)
            with fact_check_container.container():
                if items:
                    for item in sorted(list(set(items))):
                        st.page_link(f"https://www.google.com/search?q={item}", label=f"📌 {item} 확인", icon="🔍")
                else:
                    st.info("추출된 번호가 없어.")
