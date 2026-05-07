import streamlit as st
import google.generativeai as genai
import re

# 1. API 설정
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# 2. UI 설정
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

# 3. 시스템 지시어
system_rules = "당신은 최고의 공인노무사입니다. [쟁점-근거-검토-결론] 순으로 답하고 출처를 명시하세요."

# 4. 질문 처리 (2단계 시도: 검색 포함 -> 검색 제외)
if prompt := st.chat_input("노무 이슈를 입력해봐, 윤민아!"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("최적의 경로로 분석 중..."):
            history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} 
                       for m in st.session_state.messages[:-1]]
            
            result_text = ""
            active_engine = ""

            # 시도할 모델 리스트 (안정적인 별칭 우선)
            models_to_try = [
                "gemini-1.5-pro",   # 1.5 Pro 안정 버전
                "gemini-1.5-flash", # 1.5 Flash 안정 버전
                "gemini-3-flash-preview" # 3 Flash
            ]

            # 로직: 각 모델에 대해 [검색 켜고 시도 -> 실패 시 검색 끄고 시도]
            for model_id in models_to_try:
                if result_text: break
                
                # 1차 시도: 검색 기능 켜기
                try:
                    model = genai.GenerativeModel(model_id, system_instruction=system_rules, tools=[{"google_search_retrieval": {}}])
                    response = model.start_chat(history=history).send_message(prompt)
                    result_text = response.text
                    active_engine = f"{model_id} (검색 적용)"
                except:
                    # 2차 시도: 검색 기능 끄기 (리소스 절약)
                    try:
                        model = genai.GenerativeModel(model_id, system_instruction=system_rules)
                        response = model.start_chat(history=history).send_message(prompt)
                        result_text = response.text
                        active_engine = f"{model_id} (기본 모드)"
                    except:
                        continue # 다음 모델로 패스

            if not result_text:
                result_text = "🚨 윤민아, 지금 구글 무료 티어 한도를 완전히 초과한 것 같아. API 키를 새로 발급받거나, 구글 클라우드에서 유료 계정(Pay-as-you-go)을 등록하면 바로 해결될 거야!"

            st.markdown(result_text)
            st.session_state.messages.append({"role": "assistant", "content": result_text})
            engine_status.info(f"사용 엔진: **{active_engine}**")

            # 팩트체크 링크 (기존 로직)
            items = re.findall(r'([가-힣]+\d*과-\d+|[가-힣]+\s?\d{5}-\d+|\d{4}[가-힣]+\s?\d+)', result_text)
            with fact_check_container.container():
                if items:
                    for item in sorted(list(set(items))):
                        st.page_link(f"https://www.google.com/search?q={item}", label=f"📌 {item} 확인", icon="🔍")
