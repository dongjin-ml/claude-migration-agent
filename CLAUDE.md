# Claude Migration Agent

## Overview

Claude 모델 마이그레이션을 도와주는 CLI 에이전트. 타겟 모델만 지정하면 고객 코드를 자동 스캔하고 마이그레이션 이슈를 찾아 수정해준다.

## Architecture

- **Framework**: Claude Agent SDK (`claude-agent-sdk==0.1.56`)
- **LLM Backend**: Anthropic API 직접 호출 (`ANTHROPIC_API_KEY`)
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

## 네 가지 모드

### scan 모드
```bash
uv run python main.py scan --target haiku-4.5 ./customer-project
```
1. 코드 스캔 + 리포트 `report/` 디렉토리에 저장
2. "Apply fixes? (y/n)" 터미널 확인
3. y → 원본 `_prev` 백업 후 코드 자동 수정
4. n → 리포트만 남기고 종료

### eval 모드
```bash
uv run python main.py eval --target haiku-4.5 ./customer-project
```
고객이 정의한 테스트 케이스(eval_cases.json)를 소스/타겟 모델로 각각 실행.
키워드 체크 + LLM-as-Judge로 품질 점수(1-5) + 소스 대비 비교.
결과 리포트를 `report/` 디렉토리에 저장.

### autopilot 모드
```bash
uv run python main.py autopilot --target haiku-4.5 ./customer-project
```
scan → fix → eval 자동 반복. eval 통과 시 종료, 실패 시 재시도 (최대 3회, --max-iterations로 조정 가능).
전제 조건: eval_cases.json 필수 + regression 타입 케이스 필수.

### guide 모드
```bash
uv run python main.py guide --target sonnet-4.6
```
대화형 Q&A. 스킬 지식 기반으로 마이그레이션 질문에 응답.

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
├── main.py                     # CLI 엔트리포인트 (scan/eval/autopilot/guide)
├── .env.example                # ANTHROPIC_API_KEY
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
│       ├── guide.md            # guide 모드 프롬프트
│       └── evaluator.md        # eval 모드 프롬프트 (LLM-as-Judge)
├── report/                     # 스캔/eval 리포트 저장
├── .claude/skills/             # 마이그레이션 지식 (SDK 빌트인 디스커버리)
│   ├── migrate-to-haiku-45/    # 14개 Item
│   ├── migrate-to-sonnet-45/   # 15개 Item
│   ├── migrate-to-sonnet-46/   # 19개 Item
│   └── migrate-to-opus-46/     # 26개 Item
│       ├── SKILL.md
│       └── references/
└── test-project/               # 테스트용 샘플 코드
    ├── sample_app.py           # Haiku 3 / Sonnet 4 코드
    ├── sample_app_46.py        # Sonnet 4.5 / Opus 4.5 코드
    └── eval_cases.json         # eval 테스트 케이스 예제
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
- [x] test-project에 4.6 타겟용 샘플 코드 추가
- [x] 프롬프트 마이그레이션: 각 스킬에 타겟 모델 특성에 맞는 프롬프트 Item 세분화
- [x] 고객 중심 eval 시스템: eval 커맨드 + eval_cases.json(type 필드) + LLM-as-Judge
- [x] autopilot 모드: scan → fix → eval 자동 반복 (regression 케이스 필수 검증)
- [x] 리포트 시스템: report/ 디렉토리에 타임스탬프 파일로 저장
- [x] README 작성 (설치, 사용법, eval_cases.json 작성 가이드, autopilot 전제조건)

### 남은 작업 (다음 세션에서 이어서 할 것)

**우선순위 1: 모든 모드 테스트**
백그라운드 에이전트가 autopilot 모드를 추가하고 여러 파일을 수정했음.
모든 모드가 정상 동작하는지 전체 테스트 필요.
- [ ] scan 모드: `uv run python main.py scan --target haiku-4.5 ./test-project`
- [ ] eval 모드: `uv run python main.py eval --target haiku-4.5 ./test-project`
- [ ] autopilot 모드: `uv run python main.py autopilot --target haiku-4.5 ./test-project`
- [ ] guide 모드: `uv run python main.py guide --target haiku-4.5` (tmux로 테스트)
- [ ] 다른 타겟으로도 실행 확인 (sonnet-4.6 등)
- [ ] 문제 발견 시 수정 후 커밋

**우선순위 2: 추가 개선**
- [ ] guide 모드가 진짜 필요한가? 고민해보기

**완료:**
- [x] git 초기화 및 첫 커밋 (https://github.com/dongjin-ml/claude-migration-agent)

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
