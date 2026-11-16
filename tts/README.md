# 대본 → 한국어 남성 TTS → FilmCraft

기본 음성: `ko-KR-InJoonNeural` (한국어 남성).
edge-tts 7.3.1, API 키 없이 Microsoft Edge 온라인 TTS를 사용하는 오픈소스 클라이언트입니다.
대본은 음성 합성을 위해 해당 서비스로 전송되며 네트워크 연결이 필요합니다.
공식 상용 TTS API가 아니므로 서비스 변경 시 재검증이 필요합니다.

## 음성 생성

UTF-8 텍스트 파일에 읽을 문장만 작성합니다. 연출 지시나 장면 번호도 넣으면 그대로 읽습니다.

```bash
/workspace/filmcraft/bin/filmcraft-tts \
  --script /absolute/script.txt \
  --out /workspace/filmcraft/tts/take-001
```

결과: narration.mp3, 48kHz 모노 PCM narration.wav, 문장 타이밍 narration.srt, manifest.json.
자막 시간은 음성 시작 기준입니다. 오디오 시작을 미루면 영상 자막 시간도 별도로 맞춰야 합니다.
기본 속도 +0%, 피치 +0Hz. `--rate=+10%`, `--pitch=-5Hz` 등으로 조절합니다.
음성·속도를 바꾸면 길이도 달라지므로 영상 컷 타이밍을 다시 맞춥니다.

## 기존 프로젝트의 새 복사본에 배치

```bash
/workspace/filmcraft/bin/filmcraft-tts \
  --script /absolute/script.txt \
  --out /workspace/filmcraft/tts/take-002 \
  --project /workspace/filmcraft/projects/seoul-reveal.fcproj \
  --save-as /workspace/filmcraft/projects/seoul-narrated.fcproj \
  --start 0
```

새 오디오 트랙에 실제 음성 길이만큼 배치합니다. 입력 프로젝트를 덮어쓰지 않습니다.
영상 길이 자동 조절, 배경음 자동 덕킹, 자막 자동 배치는 하지 않습니다.
장면별 대본을 받으면 음성 길이에 맞춰 별도로 영상과 공개 타이밍을 편집합니다.
새 출력 폴더와 새 프로젝트 파일명을 사용합니다.

## 실행 환경

가상환경: `/workspace/filmcraft/tts/.venv`.
재설치: Python 3.12 환경에서 `uv pip install --python <venv>/bin/python -r requirements.lock`.
관리 환경 CA와 HTTPS 프록시를 적용하며 TLS 검증은 유지합니다.
클라우드의 네트워크 권한이 필요하면 실행 도구에서 네트워크 권한을 부여해야 합니다.

## 검증

한국어 남성 음성 목록 조회 성공. 예문 7.68초 MP3/WAV/SRT 생성 성공.
복사한 FilmCraft 프로젝트에 A2 트랙으로 배치하고, 엔진에서 24초 오디오 믹스를 출력했습니다.
생성 MP3 전체 디코드 오류 없음. 배포 샘플: results/tts-korean-male-sample.mp3.
공식 프로젝트 문서: https://github.com/rany2/edge-tts

## 다중 음성과 단어 누적 자막 (신규)

`filmcraft-word-tts`와 `WORD-CAPTIONS.md`를 사용하세요.
세 가지 한국어 음성 선택, 단어 실측 시각, 문장 종료 초기화, FilmCraft 자막 배치가 구현되어 있습니다.
