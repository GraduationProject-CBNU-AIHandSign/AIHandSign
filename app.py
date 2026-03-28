import streamlit as st
from google import genai

# 1. API 키 설정
# 본인의 API 키를 입력하세요.
GOOGLE_API_KEY = "AIzaSyAJgXqXhEfhunwVci48Y95doWHu91GHXNI"
client = genai.Client(api_key=GOOGLE_API_KEY)

# 페이지 설정
st.set_page_config(page_title="수어 AI 학습 도우미", page_icon="🤟")

# 2. 제목 수정
st.title("🤟 수어 AI 학습 도우미")
st.markdown("---")

# 3. 대화 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 4. 이전 대화 기록 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. 채팅 입력 및 응답 처리
if prompt := st.chat_input("수어에 대해 궁금한 점을 물어보세요!"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # 요청하신 대로 'gemini-pro-latest' 모델을 사용합니다.
            response = client.models.generate_content(
                model='gemini-pro-latest', 
                contents=prompt
            )
            answer = response.text
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception as e:
            st.error(f"답변을 생성하는 중에 문제가 발생했습니다: {e}")
