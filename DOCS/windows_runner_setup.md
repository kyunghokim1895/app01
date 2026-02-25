# 🪟 본질 회복: 윈도우용 Self-hosted Runner 설정 가이드

윈도우 데스크탑을 사용하여 유튜브의 IP 차단을 완벽히 회피하고 '영상 직접 분석' 기능을 복구해 보겠습니다.

---

## 🚨 [CRITICAL] 윈도우 스크립트 실행 권한 해제 (필수)
윈도우 런너에서 파이썬 등을 설치할 때 보안 정책으로 인해 실행이 차단되는 경우가 많습니다. **반드시 아래 명령을 관리자 권한 PowerShell에서 먼저 실행해 주세요.**

1. **관리자 권한**으로 PowerShell을 엽니다.
2. 아래 명령어를 입력하고 `Y`를 누릅니다:
   ```powershell
   Set-ExecutionPolicy RemoteSigned -Scope LocalMachine
   ```

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

- 만약 컴퓨터가 꺼져 있다면, 나중에 컴퓨터를 켰을 때 대기 중이던 작업이 자동으로 실행됩니다.

---

## 🔐 고급 팁: 로그인 없이 자동화하기 (무인 운영)

**"비밀번호를 입력하기 전에도 런너는 이미 작동 중입니다!"**

1. **로그인 불필요**: 아까 설정 시 'Service'로 등록하셨기 때문에, 윈도우가 **로그인 화면(비밀번호 입력 창)**에만 머물러 있어도 배경에서는 런너가 이미 깃허브와 연결되어 일을 시작합니다. 굳이 로그인을 하실 필요가 없습니다.
2. **자동 부팅 설정 (BIOS)**: 컴퓨터 전원을 켤 때 `Del` 또는 `F2`를 눌러 BIOS 설정에 들어가면 **'Restore on AC Power Loss'**나 **'RTC Alarm Power On'** 메뉴가 있습니다. 여기서 매일 아침 특정 시간에 컴퓨터가 자동으로 켜지게 설정하면 100% 무인 자동화가 완성됩니다.
3. **화면 꺼짐/절전 모드**: '제어판 -> 전원 옵션'에서 **'절전 모드'는 해제**하고 '화면만 끄기'로 설정해 주세요. 절전 모드에 들어가면 런너가 잠들 수 있습니다.

---

### ✅ 이제 준비가 끝났습니다!
윈도우 터미널에서 `./run.cmd`가 실행 중인 상태에서 GitHub Action의 **"Run workflow"**를 누르시면, 이제 집 컴퓨터가 유튜브를 직접 분석하기 시작합니다!
