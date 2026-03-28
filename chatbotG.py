import google.generativeai as genai

# 1. 복사해둔 API 키 설정
GOOGLE_API_KEY = "AIzaSyAJgXqXhEfhunwVci48Y95doWHu91GHXNI"
genai.configure(api_key=GOOGLE_API_KEY)

# 2. 모델 선택 (gemini-1.5-flash 모델이 응답 속도가 빠르고 챗봇용으로 매우 좋습니다)
model = genai.GenerativeModel('gemini-pro')

# 3. 챗봇 세션 시작 (대화 기록을 자동으로 저장해 줍니다)
chat = model.start_chat(history=[])

print("제미나이 챗봇이 준비되었습니다! (종료하려면 '끝' 입력)")
print("-" * 50)

# 4. 대화 루프 만들기
while True:
    user_input = input("나: ")
    
    if user_input.strip() == '끝':
        print("챗봇: 대화를 종료합니다. 수고하셨습니다!")
        break
        
    # 제미나이에게 메시지 전송 후 답변 받기
    response = chat.send_message(user_input)
    print(f"챗봇: {response.text}")
    print("-" * 50)
