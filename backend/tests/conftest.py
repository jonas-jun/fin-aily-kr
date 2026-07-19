import os


# 일부 실행 환경은 DEBUG에 불리언이 아닌 값을 주입한다. 테스트 설정은 명시적으로 고정한다.
os.environ["DEBUG"] = "false"
