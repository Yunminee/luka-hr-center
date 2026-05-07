import streamlit as st
import google.generativeai as genai
import re

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

st.set_page_config(page_title="루카 리서치 센터", layout="wide")
st.title("⚖️ 루카의 실시간 법률 리서치 센터")

# 1. 사이드바에 '실시간 검색' 스위치 추가
with st.sidebar:
    st.header("⚙️ 컨트롤 타워")
    # 이 스위치가 핵심이야, 윤민아!
    search_mode = st.toggle("🌐 실시간 법령/판례 검색 활성화", value=False, 
                            help="켜면 구글 검색을 통해 최신 정보를 가져오지만, 응답이 조금 느려지거나 할당량이 빨리 소진될 수 있어.")
    
    st.divider()
    st.header("🔍 팩트체크")
    fact_check_container = st.empty()
    engine_status = st.empty()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 2. 시스템 지시어 (검색 모드에 따라 강조점 변경)
base_rules = "당신은 최고의 공인노무사입니다. [쟁점-근거-검토-결론] 순으로 답하세요."
if search_mode:
    system_rules = base_rules + " 반드시 구글 검색을 통해 2025~2026년 최신 개정법과 판례를 확인하고 출처 링크를 달아주세요."
else:
    system_rules = base_rules + " 현재 지식을 바탕으로 빠르게 답변하되, 최신 개정 사항은 확인이 필요할 수 있음을 안내하세요."

# 3. 질문 처리
if prompt := st.chat_input("최신 법령 확인이 필요하면 왼쪽 스위치를 켜줘!"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("윤민이를 위해 가장 정확한 정보를 찾는 중..."):
            history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} 
                       for m in st.session_state.messages[:-1]]
            
            # 검색 도구 설정 (스위치가 켜졌을 때만 작동)
            tools = [{"google_search_retrieval": {}}] if search_mode else None
            
            try:
                # 3 Flash를 기본으로 하되, 검색 모드 적용
                model = genai.GenerativeModel('gemini-3-flash-preview', 
                                              system_instruction=system_rules,
                                              tools=tools)
                response = model.start_chat(history=history).send_message(prompt)
                result_text = response.text
                status_msg = "3 Flash (실시간 검색 중)" if search_mode else "3 Flash (빠른 모드)"
            except Exception as e:
                if "429" in str(e) or "ResourceExhausted" in str(e):
                    result_text = "🚨 윤민아, 실시간 검색 할당량을 다 썼나 봐. 왼쪽 스위치를 끄고 다시 물어봐 줄래? 💖"
                else:
                    result_text = f"🚨 오류가 발생했어: {e}"
                status_msg = "에러 발생"

            st.markdown(result_text)
            st.session_state.messages.append({"role": "assistant", "content": result_text})
            engine_status.info(f"현재 모드: **{status_msg}**")

            # 팩트체크 링크 추출
            items = re.findall(r'([가-힣]+\d*과-\d+|[가-힣]+\s?\d{5}-\d+|\d{4}[가-힣]+\s?\d+)', result_text)
            with fact_check_container.container():
                if items:
                    for item in sorted(list(set(items))):
                        st.page_link(f"https://www.google.com/search?q={item}", label=f"📌 {item} 확인", icon="🔍")
