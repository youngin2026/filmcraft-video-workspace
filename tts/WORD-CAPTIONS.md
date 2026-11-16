# 다양한 음성과 단어 누적 자막

## 음성 선택

기본은 사용자가 선택했던 한국어 남성입니다.

| 별칭 | 음성 ID | 종류 |
|---|---|---|
| male | ko-KR-InJoonNeural | 한국어 남성 |
| male2 | ko-KR-HyunsuMultilingualNeural | 한국어 남성 |
| female | ko-KR-SunHiNeural | 한국어 여성 |

위 세 음성은 같은 예문으로 실제 합성 확인했습니다. 다른 언어 음성은 카탈로그에서 ID를 선택할 수 있으며 사용 시 합성을 검증합니다.

```bash
/workspace/filmcraft/bin/filmcraft-word-tts --list-voices
/workspace/filmcraft/bin/filmcraft-word-tts --list-voices --locale all
/workspace/filmcraft/bin/filmcraft-word-tts --refresh-voices
```

## 대본 형식

UTF-8 TXT로 한 줄에 한 문장을 작성하는 것을 권장합니다.
같은 줄의 마침표·물음표·느낌표도 문장 구분으로 처리합니다.
숫자·약어는 실제 읽을 형태로 풀어 씁니다(예: `4위` → `사 위`). 소수점이나 약어의 점도 문장 구분으로 인식하므로 읽을 말로 바꿉니다.
연출 지시는 대본에 넣지 않습니다. 한 문장이 자막 상자보다 길면 짧은 문장들로 나눕니다.

```text
나는 맛있는 밥이 먹고싶다.
다음 문장은 새롭게 시작합니다.
```

## 작동 방식

- 띄어쓰기 기준으로 단어를 분리합니다. 문장별로 자연스럽게 TTS를 합성합니다.
- TTS 서비스가 반환한 실제 WordBoundary 시각을 사용합니다. 균등 분할로 타이밍을 추정하지 않습니다.
- `나는` → `나는 맛있는` → `나는 맛있는 밥이` → `나는 맛있는 밥이 먹고싶다`.
- 마지막 단어의 발음이 끝나면 자막 전체가 지워집니다. 다음 문장은 다시 첫 단어부터 쌓입니다.
- 기본 문장 사이 추가 간격은 0.25초입니다. 서비스 자체의 앞뒤 무음도 있으므로 실제 간격은 더 길 수 있습니다.
- 서비스가 단어를 세부 토큰으로 나누면 원문 어절로 묶습니다. 원문과 맞지 않거나 어절 내부의 발음 시각이 없으면 임의 추정하지 않고 오류를 표시합니다.
- 화면의 변경 시점은 영상 프레임 단위로 반올림됩니다(30fps에서는 최대 약 17ms). 한 프레임보다 짧은 단어 상태는 합쳐질 수 있습니다.

## 음성과 자막 파일만 생성

```bash
/workspace/filmcraft/bin/filmcraft-word-tts \
  --script /absolute/script.txt --out /workspace/filmcraft/tts/take-003 \
  --voice female --rate=+0% --pitch=+0Hz
```

`narration.wav`(48kHz 모노), `narration.mp3`, 누적 자막 `narration.srt`, 단어·문장·화면별 시각 `timing.json`을 만듭니다.
문장별 원음과 원본 단어 시각도 보존합니다. SRT 시각은 음성 시작 기준입니다.

## FilmCraft에 음성과 누적 자막 함께 배치

```bash
/workspace/filmcraft/bin/filmcraft-word-tts \
  --script /absolute/script.txt --out /workspace/filmcraft/tts/take-004 \
  --voice male2 \
  --project /workspace/filmcraft/projects/seoul-reveal.fcproj \
  --save-as /workspace/filmcraft/projects/seoul-word-narration.fcproj
```

새 오디오 트랙과 새 그래픽 트랙을 추가합니다. 기존 프로젝트를 덮어쓰지 않습니다.
`--project` 없이 `--save-as`만 주면 1080×1920, 30fps, 검은 배경의 새 데모를 만듭니다.
자막 위치는 `--x 90 --y 1300 --width 900 --height 480 --size 64`가 기본입니다. 좌표와 크기는 픽셀 단위이므로 다른 해상도에서는 조절합니다.
기존 배경음 자동 덕킹이나 사진 컷 길이 조절은 하지 않습니다. 최종 영상에서는 실제 대본에 맞춰 별도로 조절합니다.

## 합성한 타이밍으로 다시 배치

```bash
/workspace/filmcraft/bin/filmcraft-word-tts \
  --timing /workspace/filmcraft/tts/take-003/timing.json \
  --project /workspace/filmcraft/projects/seoul-reveal.fcproj \
  --save-as /workspace/filmcraft/projects/seoul-caption-revision.fcproj --start 0
```

네트워크 재호출 없이 보관한 WAV와 타이밍을 사용합니다.
새 출력 폴더와 새 프로젝트 파일명을 사용하세요. 실패 시 이미 생성한 음성/타이밍은 보존됩니다.

## 검증 및 샘플

- 한국어 3종 실제 합성, 한국어 어절/하위토큰/불일치 거부/문장 구분 테스트 4개 통과.
- 두 문장 8개 누적 상태를 FilmCraft 그래픽으로 배치해 영상 출력.
- 출력 영상에서 발음 전·문장 종료 후 자막이 없는 프레임과 발음 중 자막이 있는 프레임 확인.
- 기존 서울 영상 복사본에 오디오 1트랙과 그래픽 1트랙을 추가하고 8개 자막 클립 확인.
- 샘플 영상: `results/tts-word-reveal-demo.mp4` (1080×1920, 30fps, 약 7.2초).
- 음성 비교: `results/tts-voice-injoon.mp3`, `tts-voice-hyunsu.mp3`, `tts-voice-sunhi.mp3`.

기반은 기존 Python edge-tts 7.3.1입니다. 온라인 서비스로 대본이 전송되며 네트워크 연결이 필요합니다.
