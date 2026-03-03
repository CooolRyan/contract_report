# 로컬 API 키 설정 (GitHub 노출 방지)

키움 API 키·계좌번호는 **절대 config.yaml 에 직접 넣지 마세요.**  
로컬에서는 `.env` 파일로 넣고, 이 파일은 Git 에 올라가지 않습니다.

## 1. .env 파일 만들기

`quant-trader` 폴더에서:

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# macOS / Linux
cp .env.example .env
```

## 2. .env 에 실제 값 넣기

`.env` 파일을 열어 placeholder 를 본인 키로 바꿉니다.

```env
KIWOOM_APPKEY=발급받은_APPKEY
KIWOOM_SECRETKEY=발급받은_SECRETKEY
KIWOOM_ACCOUNT=사용할_계좌번호
```

- `broker_mode: mock` 만 쓸 때는 비워 두어도 됩니다.
- `broker_mode: rest` → APPKEY, SECRETKEY, ACCOUNT 모두 필요.
- `broker_mode: openapi` → ACCOUNT 만 있어도 됩니다 (계좌 선택용).

## 3. 동작 방식

- `main.py` 실행 시 **quant-trader/.env** 를 읽어 환경 변수로 넣습니다.
- `load_config()` 가 이미 **환경 변수를 config.yaml 값보다 우선** 사용하므로, `.env` 에 넣은 값이 자동으로 적용됩니다.
- **.env** 는 프로젝트 루트 `.gitignore` 에 포함되어 있어 **Git 에 커밋되지 않습니다.**
- **.env.example** 만 저장소에 있고, 실제 키는 들어 있지 않습니다.

## 4. 주의사항

- `.env` 파일을 다른 사람과 공유하거나, 슬랙/메일 등에 붙여 넣지 마세요.
- `.env` 가 실수로 커밋된 적이 있다면, 해당 파일을 Git 히스토리에서 제거하고 키를 재발급하는 것이 안전합니다.
