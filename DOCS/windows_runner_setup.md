# 🪟 본질 회복: 윈도우용 Self-hosted Runner 설정 가이드

윈도우 데스크탑을 사용하여 유튜브의 IP 차단을 완벽히 회피하고 '영상 직접 분석' 기능을 복구해 보겠습니다.

---

## 🏗️ 0단계: 집 컴퓨터 필수 도구 설치
작업을 시작하기 전에 아래 도구들이 설치되어 있어야 합니다.

1. **Python**: [python.org](https://www.python.org/)에서 3.10 이상 버전을 설치 (설치 시 "Add Python to PATH" 반드시 체크!)
2. **Git**: [git-scm.com](https://git-scm.com/)에서 설치
3. **FFmpeg (필수)**: 터미널(PowerShell)을 열고 아래 명령어를 입력하여 설치하세요:
   ```powershell
   winget install ffmpeg
   ```
   *(설치 후 터미널을 껐다 켜야 적용됩니다.)*

---

## 1단계: 프로젝트 클론 (Clone)
윈도우 터미널에서 아래 명령을 실행하여 코드를 내려받습니다:
```bash
git clone https://github.com/kyunghokim1895/app01.git
cd app01
pip install -r requirements.txt
```

---

## 2단계: GitHub에서 윈도우 런너 생성
1. [GitHub 저장소 Settings](https://github.com/kyunghokim1895/app01/settings/actions/runners)로 이동합니다.
2. **New self-hosted runner** 버튼을 클릭합니다.
3. Runner image에서 **Windows**, Architecture에서 **x64**를 선택합니다.

---

## 3단계: PowerShell에서 명령 실행
GitHub 페이지 하단의 **Download** 섹션과 **Configure** 섹션의 명령어를 **PowerShell**에 하나씩 복사해서 붙여넣으세요.

#### 💡 설정 팁:
- `./config.cmd` 실행 시 물어보는 질문들은 모두 **엔터(Enter)**를 눌러 기본값으로 설정하세요.
- 마지막에 `./run.cmd`를 실행하면 런너가 가동됩니다!

---

## ❓ 자주 묻는 질문: "컴퓨터를 항상 켜두어야 하나요?"

**아니요, 특정 시간에만 켜져 있으면 됩니다!**
- 매일 아침 업데이트를 원하신다면 그 시간에만 컴퓨터가 켜져 있으면 됩니다.
- 윈도우의 '작업 스케줄러'를 사용하여 컴퓨터가 자동으로 켜지게 설정할 수도 있습니다.
- 만약 컴퓨터가 꺼져 있다면, 나중에 컴퓨터를 켰을 때 대기 중이던 작업이 자동으로 실행됩니다.

---

### ✅ 이제 준비가 끝났습니다!
윈도우 터미널에서 `./run.cmd`가 실행 중인 상태에서 GitHub Action의 **"Run workflow"**를 누르시면, 이제 집 컴퓨터가 유튜브를 직접 분석하기 시작합니다!
