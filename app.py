import streamlit as st
import google.generativeai as genai
import re

# 1. API 설정
# 수정 후의 코드 (이대로 복사해서 붙여넣으세요)
GOOGLE_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GOOGLE_API_KEY)

# 2. UI 및 세션 설정
st.set_page_config(page_title="루카 리서치 센터", layout="wide")
st.title("⚖️ 루카의 노동법률 리서치&토론 센터")

# 사이드바 레이아웃 (팩트체크 영역 부활)
with st.sidebar:
    st.header("🔍 실시간 팩트체크")
    st.caption("답변 내 판례 및 행정해석 추출")
    fact_check_container = st.empty() # 실시간 업데이트를 위한 공간
    st.divider()
    engine_status = st.empty() # 현재 어떤 엔진이 도는지 표시

if "messages" not in st.session_state:
    st.session_state.messages = []

# 기존 대화 내역 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 3. 전문가 페르소나 지시문
def get_expert_prompt(user_query):
    return f"""
    당신은 대한민국 법학박사 학위를 보유한 30년 경력의 수석 노무사입니다.
    질의에 대해 단순 답변이 아닌, 법원의 판단 기조와 고용노동부의 행정해석을 
    입체적으로 분석하여 실무적 해법을 제시하십시오.
    
    [필수 분석 구조]
    1. 사안의 쟁점 파악
    2. 근거 법령 및 판례/행정해석 (번호 필수 명시)
    3. 심층 법리 검토 (유불리 판단)
    4. 결론 및 리스크 대응 방안
    
    질의: {user_query}
    """

# 4. 질문 처리 및 팩트체크 로직
if prompt := st.chat_input("노무 이슈를 입력하세요."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("전문 법리 분석 중..."):
            full_instruction = get_expert_prompt(prompt)
            result_text = ""
            active_engine = ""

            try:
                # [시도 1] 최강의 추론 엔진 3.1 Pro
                target_model = genai.GenerativeModel('gemini-3.1-pro-preview')
                response = target_model.generate_content(full_instruction)
                result_text = response.text
                active_engine = "Gemini 3.1 Pro"

            except Exception as e:
                # [시도 2] 한도 초과 시 Flash-Lite 투입
                if "429" in str(e):
                    try:
                        lite_model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')
                        response = lite_model.generate_content(full_instruction)
                        result_text = response.text
                        active_engine = "Gemini 3.1 Flash-Lite (백업)"
                    except Exception as e2:
                        result_text = f"🚨 모든 엔진 응답 불가: {e2}"
                else:
                    result_text = f"🚨 시스템 오류: {e}"

            # 최종 답변 출력
            st.markdown(result_text)
            st.session_state.messages.append({"role": "assistant", "content": result_text})
            
            # 사이드바 엔진 정보 업데이트
            engine_status.info(f"사용 중인 엔진: **{active_engine}**")

            # --- 팩트체크 번호 추출 로직 (부활) ---
            # 대법원 판례, 행정해석 번호 패턴 매칭
            pattern = r'([가-힣]+\d*과-\d+|[가-힣]+\s?\d{5}-\d+|\d{4}[가-힣]+\s?\d+)'
            items = re.findall(pattern, result_text)
            
            with fact_check_container.container():
                if items:
                    unique_items = sorted(list(set(items)))
                    for item in unique_items:
                        st.write(f"📌 **{item}**")
                        # 구글 검색 링크 자동 생성
                        search_url = f"https://www.google.com/search?q={item}+판례+행정해석"
                        st.page_link(search_url, label="원문 확인", icon="🔍")
                else:
                    st.info("현재 답변에서 추출된 인용 번호가 없습니다.")
