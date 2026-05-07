import streamlit as st
import google.generativeai as genai
import re

# 1. API 설정
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# 2. UI 및 세션 설정
st.set_page_config(page_title="루카 리서치 센터", layout="wide")
st.title("⚖️ 루카의 실시간 법률 리서치 센터")

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

# 3. 강화된 시스템 지시어 (환각 방지 및 출처 표기)
system_rules = """
당신은 대한민국 최고의 공인노무사이자 법률 리서치 전문가입니다.
1. [구글 검색 활용]: 모든 답변 작성 전, 'google_search_retrieval' 도구를 사용하여 최신 판례와 고용노동부 행정해석을 반드시 검색하십시오.
2. [출처 표기]: 정보의 근거가 된 문장 끝에 [1], [2]와 같이 번호를 매기고, 답변 하단에 '참고 자료' 섹션을 만들어 해당 번호의 제목과 URL 링크를 목록 형태로 제공하십시오.
3. [대화 모드]: 새로운 사안은 [쟁점-근거-검토-결론] 4단계로 보고하고, 추가 질문에는 전문가 동료처럼 자연스럽게 토론하십시오.
4. [정직성]: 검색 결과에 없는 정보를 지어내지 마십시오. 판례 번호가 불확실하면 "확인이 필요하다"고 솔직하게 답하십시오.
"""

# 4. 질문 처리 및 2단 스위칭 로직 (에러 핸들링 강화)
if prompt := st.chat_input("확인이 필요한 노무 이슈를 입력해봐, 윤민아!"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("구글 검색 및 법리 검토 중..."):
            # 대화 기록 구성 (맥락 유지)
            history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} 
                       for m in st.session_state.messages[:-1]]

            result_text = ""
            active_engine = ""
            
            # 구글 검색 도구 정의
            tools = [{"google_search_retrieval": {}}]

            try:
                # [1순위] 3.1 Pro Preview 시도
                model = genai.GenerativeModel('gemini-3.1-pro-preview', 
                                              system_instruction=system_rules,
                                              tools=tools)
                active_engine = "Gemini 3.1 Pro (검색 연동)"
                chat = model.start_chat(history=history)
                response = chat.send_message(prompt)
                result_text = response.text
                
            except Exception as e:
                # 할당량 초과(ResourceExhausted) 시 2순위 Flash로 전환
                if "429" in str(e) or "ResourceExhausted" in str(e):
                    try:
                        model = genai.GenerativeModel('gemini-3-flash-preview', 
                                                      system_instruction=system_rules,
                                                      tools=tools)
                        active_engine = "Gemini 3 Flash (백업/검색 연동)"
                        chat = model.start_chat(history=history)
                        response = chat.send_message(prompt)
                        result_text = response.text
                    except Exception as e2:
                        result_text = "🚨 윤민아, 지금 구글 서버가 너무 바빠서 응답을 못 한대. 1분만 쉬었다가 다시 물어봐 줄래? 💖"
                else:
                    result_text = f"🚨 분석 중 오류가 발생했어: {e}"

            # 결과 출력
            if active_engine:
                st.caption(f"✅ {active_engine} 엔진 분석 완료")
            st.markdown(result_text)
            st.session_state.messages.append({"role": "assistant", "content": result_text})
            
            # 사이드바 상태 업데이트
            engine_status.info(f"사용 엔진: **{active_engine}**")

            # --- 사이드바 팩트체크 추출 ---
            pattern = r'([가-힣]+\d*과-\d+|[가-힣]+\s?\d{5}-\d+|\d{4}[가-힣]+\s?\d+)'
            items = re.findall(pattern, result_text)
            
            with fact_check_container.container():
                if items:
                    for item in sorted(list(set(items))):
                        st.page_link(f"https://www.google.com/search?q={item}", label=f"📌 {item} 확인", icon="🔍")
                else:
                    st.info("추출된 번호 없음")
