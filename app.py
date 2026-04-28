import streamlit as st
import google.generativeai as genai
import re

# 1. API 설정
GOOGLE_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GOOGLE_API_KEY)

# 2. UI 및 세션 설정
st.set_page_config(page_title="루카 리서치 센터", layout="wide")
st.title("⚖️ 루카의 노동법률 리서치&토론 센터")

# 사이드바 레이아웃
with st.sidebar:
    st.header("🔍 실시간 팩트체크")
    st.caption("답변 내 판례 및 행정해석 추출")
    fact_check_container = st.empty()
    st.divider()
    engine_status = st.empty()

if "messages" not in st.session_state:
    st.session_state.messages = []

# 기존 대화 내역 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 3. 시스템 지시어 (페르소나 및 환각 방지)
system_rules = """
당신은 대한민국 최고 수준의 공인노무사이자 노동법률 전문가입니다.
1. [대화 방식]: 새로운 사안은 [1. 쟁점, 2. 근거, 3. 법리 검토, 4. 결론] 4단계로 보고하고, 이어진 대화나 토론은 격식 없이 전문가 동료처럼 자연스럽게 진행하십시오.
2. [팩트체크 엄수]: 판례 및 행정해석 번호는 100% 확실한 경우에만 작성하십시오. 절대 번호를 임의로 지어내지 마십시오. 모를 경우 솔직하게 확인이 필요하다고 답변하십시오.
"""

# 4. 질문 처리 및 새로운 3단 스위칭 로직 (Latest 모델 적용)
if prompt := st.chat_input("노무 이슈를 입력하세요 (또는 이전 답변에 대해 질문하세요)."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("최적의 엔진을 찾아 분석 중..."):
            result_text = ""
            active_engine = ""

            # 대화 기록 구성
            gemini_history = []
            for msg in st.session_state.messages[:-1]:
                role = "user" if msg["role"] == "user" else "model"
                gemini_history.append({"role": role, "parts": [msg["content"]]})

            # [1단계] Gemini 3.1 Pro Preview (가장 최신 시도)
            try:
                target_model = genai.GenerativeModel('gemini-3.1-pro-preview', system_instruction=system_rules)
                chat = target_model.start_chat(history=gemini_history)
                response = chat.send_message(prompt)
                result_text = response.text
                active_engine = "Gemini 3.1 Pro (Preview)"
            
            except Exception:
                # [2단계] Gemini Pro Latest (주력 프로 모델 시도)
                try:
                    target_model = genai.GenerativeModel('gemini-pro-latest', system_instruction=system_rules)
                    chat = target_model.start_chat(history=gemini_history)
                    response = chat.send_message(prompt)
                    result_text = response.text
                    active_engine = "Gemini Pro Latest (주력)"
                
                except Exception:
                    # [3단계] Gemini Flash Latest (빠른 백업 모델 시도)
                    try:
                        target_model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=system_rules)
                        chat = target_model.start_chat(history=gemini_history)
                        response = chat.send_message(prompt)
                        result_text = response.text
                        active_engine = "Gemini Flash Latest (백업)"
                    except Exception:
                        result_text = "🚨 현재 모든 서비스 점검 중이거나 API 호출 한도를 초과했습니다."

            # 결과 출력
            if active_engine:
                st.caption(f"✅ {active_engine} 엔진 분석 완료 (맥락 유지 모드)")
            st.markdown(result_text)
            st.session_state.messages.append({"role": "assistant", "content": result_text})
            
            engine_status.info(f"사용 중인 엔진: **{active_engine}**")

            # --- 팩트체크 번호 추출 로직 ---
            pattern = r'([가-힣]+\d*과-\d+|[가-힣]+\s?\d{5}-\d+|\d{4}[가-힣]+\s?\d+)'
            items = re.findall(pattern, result_text)
            
            with fact_check_container.container():
                if items:
                    unique_items = sorted(list(set(items)))
                    for item in unique_items:
                        st.write(f"📌 **{item}**")
                        search_url = f"https://www.google.com/search?q={item}+판례+행정해석"
                        st.page_link(search_url, label="원문 확인", icon="🔍")
                else:
                    st.info("추출된 인용 번호가 없습니다.")
