# Claude Migration Agent

## Overview

Claude 모델 마이그레이션을 도와주는 CLI 에이전트. 타겟 모델만 지정하면 고객 코드를 자동 스캔하고 마이그레이션 이슈를 찾아 수정해준다.

## Architecture

- **Framework**: Claude Agent SDK (`claude-agent-sdk==0.1.56`)
- **LLM Backend**: `.env`의 `BACKEND=api|vertex` 스위치로 Anthropic API / Google Vertex AI 전환 (`anthropic[vertex]` extras로 `google-auth` 포함)
- **Interface**: CLI (argparse, `main.py` 엔트리포인트)
- **Python**: 3.12
- **패키지 관리**: uv (`setup/` 디렉토리 기반, 루트에 심링크)
- **프로젝트 구조**: `sample-deep-insight/self-hosted` 패턴 따름

## 마이그레이션 지식 관리

마이그레이션 지식은 **스킬 형태**(SKILL.md + references)로 `.claude/skills/`에 배치.
Claude Agent SDK의 빌트인 스킬 디스커버리/로더가 자동 처리하며,
프롬프트에서 스킬 이름을 명시적으로 지정하여 정확한 매칭을 보장한다.

각 스킬은 API 코드 변경 + 프롬프트 마이그레이션을 모두 Item으로 관리한다.
프롬프트 마이그레이션은 Anthropic이 "highest friction point"로 인식하는 가장 중요한 부분.

## 세 가지 모드

### scan 모드
```bash
uv run python main.py scan --target haiku-4.5 --project-path ./customer-project
```
1. 코드 스캔 + 리포트 `report/` 디렉토리에 저장
2. "Apply fixes? (y/n)" 터미널 확인
3. y → 원본 `_prev` 백업 후 코드 자동 수정
4. n → 리포트만 남기고 종료

### eval 모드
```bash
uv run python main.py eval --target haiku-4.5 --project-path ./customer-project
```
고객이 정의한 테스트 케이스(eval_cases.json)를 소스/타겟 모델로 각각 실행.
키워드 체크 + LLM-as-Judge로 품질 점수(1-5) + 소스 대비 비교.
결과 리포트를 `report/` 디렉토리에 저장.
regression 케이스 없으면 경고 후 확인 요구 (autopilot과 동일 검증).

### autopilot 모드
```bash
uv run python main.py autopilot --target haiku-4.5 --project-path ./customer-project
```
scan → fix → eval 자동 반복. eval 통과 시 종료, 실패 시 재시도 (기본 `MAX_EVAL_ITERATIONS=3`, `--max-iterations`로 per-run 오버라이드).
PASS 판정: Judge가 마지막 줄에 `VERDICT: PASS` 출력 시 종료. regression 케이스는 반드시 통과해야 함.
전제 조건: eval_cases.json 필수 + regression 타입 케이스 필수.

## 지원 타겟 모델

| 타겟 | 스킬 이름 | Item 수 | 상태 |
|------|-----------|---------|------|
| haiku-4.5 | `migrate-to-haiku-45` | 14개 | 완료 |
| sonnet-4.5 | `migrate-to-sonnet-45` | 15개 | 완료 |
| sonnet-4.6 | `migrate-to-sonnet-46` | 19개 | 완료 |
| opus-4.6 | `migrate-to-opus-46` | 26개 | 완료 |

## 프로젝트 구조

```
claude-migration-agent/
├── main.py                     # CLI 엔트리포인트 (scan/eval/autopilot)
├── .env.example                # BACKEND(api|vertex), 자격증명, 모델 설정
├── .gitignore
├── README.md                   # 사용자 가이드
├── setup/                      # uv 환경 설정
│   ├── pyproject.toml
│   ├── create-uv-env.sh
│   └── .python-version
├── src/
│   ├── __init__.py
│   └── prompts/
│       ├── __init__.py
│       ├── template.py         # apply_prompt_template()
│       ├── scanner.md          # scan 모드 프롬프트
│       ├── fixer.md            # fix 모드 프롬프트
│       └── evaluator.md        # eval 모드 프롬프트 (LLM-as-Judge)
├── report/                     # 스캔/eval 리포트 저장
├── .claude/skills/             # 마이그레이션 지식 (SDK 빌트인 디스커버리)
│   ├── migrate-to-haiku-45/    # 14개 Item
│   ├── migrate-to-sonnet-45/   # 15개 Item
│   ├── migrate-to-sonnet-46/   # 19개 Item
│   └── migrate-to-opus-46/     # 26개 Item
│       ├── SKILL.md
│       └── references/
└── customer-project/               # 테스트용 샘플 코드
    ├── sample_app.py           # Haiku 3 / Sonnet 4 코드
    ├── sample_app_46.py        # Sonnet 4.5 / Opus 4.5 코드
    ├── eval_cases.json         # eval 테스트 케이스 예제
    └── prompts/                # 외부 프롬프트 파일 (코드에서 로드)
        ├── system_prompt.txt       # Haiku 3용 시스템 프롬프트
        ├── tool_use_prompt.txt     # Haiku 3용 도구 사용 프롬프트
        ├── agent_system_prompt.txt # Sonnet 4.5용 에이전트 프롬프트 (anti-laziness 포함)
        └── analysis_prompt.txt     # Sonnet 4.5용 분석 프롬프트 (JSON prefill 패턴)
```

## 개발 진행 상황

### 완료
- [x] Phase 1: 뼈대 구축 (pyproject.toml, src/, main.py, .env, .gitignore)
- [x] Phase 2: 첫 스킬 (migrate-to-haiku-45)
- [x] Phase 3: Scan 모드 구현 + 테스트
- [x] Phase 4: Guide 모드 구현 + 테스트
- [x] scan 플로우: 리포트 저장(report/) + "Apply fixes?" + 코드 수정
- [x] 타겟 모델 유효성 검증 + 스킬 이름 명시적 지정
- [x] Phase 5: 추가 스킬 3개 (sonnet-45, sonnet-46, opus-46)
- [x] 공식 문서 + Google Doc 기준 크로스체크 및 보강
- [x] Phase 6: 각 스킬별 scan 테스트 (4개 타겟 모두 성공)
- [x] customer-project에 4.6 타겟용 샘플 코드 추가
- [x] 프롬프트 마이그레이션: 각 스킬에 타겟 모델 특성에 맞는 프롬프트 Item 세분화
- [x] 고객 중심 eval 시스템: eval 커맨드 + eval_cases.json(type 필드) + LLM-as-Judge
- [x] autopilot 모드: scan → fix → eval 자동 반복 (regression 케이스 필수 검증)
- [x] 리포트 시스템: report/ 디렉토리에 타임스탬프 파일로 저장
- [x] README 작성 (설치, 사용법, eval_cases.json 작성 가이드, autopilot 전제조건)
- [x] customer-project에 외부 프롬프트 파일 추가 (prompts/ 디렉토리) + .py에서 load_prompt()으로 로드
- [x] 스캐너 프롬프트에 코드베이스 분석 단계 추가 (API 코드 위치, 프롬프트 인라인/외부 여부 파악)
- [x] 스트리밍 출력 구현: `stream_query()` 헬퍼 + `include_partial_messages=True`
- [x] LangChain `ColoredStreamingCallback` 적용 (텍스트=white, 도구=yellow)
- [x] 도구 호출 시 input 파싱하여 상세 표시 (`[tool-use] Reading sample_app.py` 등)
- [x] `langchain-core==0.3.63` 의존성 추가
- [x] git 초기화 및 첫 커밋 (https://github.com/dongjin-ml/claude-migration-agent)

### 이번 세션에서 추가된 작업

- [x] 스트리밍 출력 UX 정리: 모드별 cyan 배너 + purple 단계 헤더 + iteration blue 서브배너 + cyan 스피너 (`Working...`)
- [x] 각 프롬프트(scanner/fixer/evaluator)에 preamble 지시 추가 (영문, 싱가폴 고객 전달용)
- [x] `.env` 환경변수 확장: `BACKEND`, `AGENT_MODEL`, `EVAL_MODEL`, `MAX_EVAL_ITERATIONS`
- [x] CLI 플래그 통일: `path` 위치인자 → `--project-path` (scan/eval/autopilot 모두)
- [x] eval 검증 일관화: `run_eval`도 `validate_eval_cases()` 사용 (regression 케이스 경고 포함)
- [x] guide 모드 제거: 함수 + argparse + 디스패처 + `guide.md` 정리, 데드 코드(`TARGET_MODELS`, `run_guide`) 삭제
- [x] Vertex AI 백엔드 지원: `BACKEND=vertex` 한 줄로 전환, `CLAUDE_CODE_USE_VERTEX=1` 자동 주입, `make_anthropic_client()` 팩토리로 `Anthropic` / `AnthropicVertex` 분기, `require_credentials()`로 백엔드별 변수 사전 검증
- [x] `anthropic[vertex]==0.89.0` extras로 변경 → `google-auth` 자동 포함
- [x] 샘플 디렉토리 이름 변경: `test-project` → `customer-project` (고객 대면 이름으로)
- [x] README 전면 재작성 (고객 배포용, 영문): 1.Prepare / 2.Install / 3.eval_cases.json / 4.Run / 5.Outputs / 6.Troubleshooting, Vertex 섹션 + BACKEND 스위치 설명 포함
- [x] README에 Customizing evaluation criteria 섹션 (Judge 프롬프트 수정 방법 + VERDICT 마커 계약 설명)
- [x] customer-project 샘플 원상복구 (Haiku 3 → Haiku 4.5 시나리오 재현 가능하도록)
- [x] 플랫폼 전제조건(macOS/Linux) + Vertex `@YYYYMMDD` 포맷 안내 README 명시

### 남은 작업 (다음 세션)

- [ ] 실제 고객 프로젝트(FSI)로 end-to-end 테스트
- [ ] Vertex 실제 GCP 계정으로 인증 → scan/eval 검증
- [ ] eval 판정 엄격도 조정 옵션 필요성 검토 (현재는 `evaluator.md` 수동 편집으로만 가능)
- [ ] 대용량 프로젝트에서 성능 측정 (scan 시간, 토큰 소모)

## 참고 리소스

- 마이그레이션 가이드: https://platform.claude.com/docs/en/about-claude/models/migration-guide
- 프롬프팅 베스트 프랙티스: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- Prompt Improver: https://console.anthropic.com (Console 내 무료 도구, 1-2분)

## Working Conventions

- 최소한의 것에서 하나씩 추가하는 방식으로 개발
- 스킬 추가 시 SKILL.md → references 순서로 일관성 확인
- 스킬 파일은 고객 전달 가능한 상태 유지 (Anthropic 내부 정보 제외)
- pyproject.toml에 패키지 버전 반드시 명시 (배포용)
- 한글 파일 작성 시 Write 도구 대신 Python 스크립트 사용 (유니코드 깨짐 방지)
