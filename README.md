# Claude Migration Agent

Claude 모델 마이그레이션을 도와주는 CLI 에이전트입니다.
타겟 모델만 지정하면 고객 코드를 자동 스캔하고, 마이그레이션 리포트를 생성하고, 코드를 자동 수정해줍니다.

## 지원 타겟 모델

| 타겟 모델 | 소스 모델 | 점검 항목 수 |
|------------|------------|------------|
| Haiku 4.5 | Haiku 3, 3.5 | 14개 |
| Sonnet 4.5 | Sonnet 4, Sonnet 3.7 | 15개 |
| Sonnet 4.6 | Sonnet 4.5, Sonnet 4 | 19개 |
| Opus 4.6 | Opus 4.5, Opus 4.1 | 26개 |

## 설치

### 1. 저장소 클론

```bash
git clone <repo-url>
cd claude-migration-agent
```

### 2. uv 환경 셋업

```bash
cd setup
./create-uv-env.sh claude-migration-agent
cd ..
```

이 스크립트가 다음을 자동 처리합니다:
- uv 설치 확인 (없으면 자동 설치)
- Python 3.12 가상환경 생성
- 의존성 설치 (`claude-agent-sdk`, `anthropic` 등)
- Jupyter 커널 등록
- 루트 디렉토리에 심링크 생성

### 3. API 키 설정

```bash
cp .env.example .env
```

`.env` 파일을 열고 Anthropic API 키를 입력합니다:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## 사용법

### Scan 모드: 코드 스캔 + 자동 수정

고객 프로젝트 디렉토리와 타겟 모델을 지정하면 자동으로 스캔합니다.

```bash
uv run python main.py scan --target haiku-4.5 /path/to/customer/project
```

**실행 플로우:**

1. 에이전트가 해당 디렉토리의 코드를 스캔
2. 마이그레이션 리포트를 `report/` 디렉토리에 저장
3. 터미널에 "Apply fixes? (y/n)" 확인
4. `y` 입력 시 원본 파일을 `_prev` 접미사로 백업하고 코드 자동 수정
5. `n` 입력 시 리포트만 남기고 종료

**예시:**

```bash
# Haiku 3 -> Haiku 4.5 마이그레이션
uv run python main.py scan --target haiku-4.5 ./my-project

# Sonnet 4.5 -> Sonnet 4.6 마이그레이션
uv run python main.py scan --target sonnet-4.6 ./my-project

# Opus 4.5 -> Opus 4.6 마이그레이션
uv run python main.py scan --target opus-4.6 ./my-project
```

### Guide 모드: 대화형 Q&A

마이그레이션에 대한 질문을 대화형으로 할 수 있습니다.

```bash
uv run python main.py guide --target sonnet-4.6
```

예시 질문:
- "Sonnet 4.6에서 prefill이 제거되었다는데, 어떻게 대응해야 하나요?"
- "effort 파라미터를 어떻게 설정해야 하나요?"
- "우리 코드에서 temperature와 top_p를 동시에 쓰고 있는데 문제가 되나요?"

`exit`를 입력하면 종료됩니다.

### Eval 모드: 마이그레이션 전후 품질 비교

구모델과 신모델의 출력을 자동 비교하고 LLM-as-Judge로 품질을 평가합니다.

```bash
uv run python main.py eval --target haiku-4.5 /path/to/eval/directory
```

**실행 플로우:**

1. `eval_cases.json`에서 테스트 케이스 로드
2. 각 케이스를 소스 모델과 타겟 모델로 각각 호출
3. LLM-as-Judge가 키워드 체크 + 품질 점수(1-5) + 비교 판정
4. 결과 리포트를 `report/` 디렉토리에 저장

#### eval_cases.json 작성 가이드

테스트 케이스 파일을 아래 형식으로 작성합니다:

```json
{
  "source_model": "claude-3-haiku-20240307",
  "target_model": "claude-haiku-4-5-20251001",
  "system_prompt": "You are a helpful assistant.",
  "cases": [
    {
      "id": 1,
      "name": "테스트 이름",
      "type": "regression",
      "input": "사용자 입력 텍스트",
      "expected_output": "기대하는 출력",
      "criteria": "평가 기준 (선택사항)"
    }
  ]
}
```

**필드 설명:**

| 필드 | 필수 | 설명 |
|-------|------|------|
| `source_model` | 예 | 현재 사용 중인 모델 ID |
| `target_model` | 예 | 마이그레이션 목표 모델 ID |
| `system_prompt` | 아니오 | 모든 케이스에 적용할 시스템 프롬프트 |
| `cases[].id` | 예 | 케이스 번호 |
| `cases[].name` | 예 | 케이스 설명 |
| `cases[].type` | 예 | 테스트 타입 (아래 표 참고) |
| `cases[].input` | 예 | 모델에 보낼 사용자 입력 |
| `cases[].expected_output` | 예 | 기대하는 출력 (키워드 체크 및 LLM 평가 기준) |
| `cases[].criteria` | 아니오 | 추가 평가 기준 (예: "한국어로 응답해야 함", "JSON 형식이어야 함") |

**type 필드 설명:**

| type | 설명 | 예시 |
|------|------|------|
| `regression` | **필수.** 현재 잘 동작하는 기능. 마이그레이션 후에도 반드시 동일하게 동작해야 함. 다른 항목 수정 시 이 케이스가 깨지면 실패 판정 | 기존 고객 대화, 핵심 비즈니스 로직, 다국어 응답 |
| `improvement` | 마이그레이션으로 개선되길 기대하는 기능. 실패해도 전체 판정에 영향 적음 | 새 기능 활용, 성능 개선, 포맷 개선 |
| `capability` | 신모델에서만 가능한 새 기능 테스트. 소스 모델에서는 실패해도 무방 | extended thinking, 64K output, adaptive thinking |

> **중요:** autopilot 모드 사용 시 `regression` 타입의 케이스가 반드시 포함되어야 합니다.
> 마이그레이션 수정으로 인해 기존 잘 되던 기능이 깨지는 것을 방지하는 것이 가장 중요합니다.

**예제 시나리오:**

```json
{
  "source_model": "claude-sonnet-4-5-20250929",
  "target_model": "claude-sonnet-4-6",
  "system_prompt": "You are a code review assistant.",
  "cases": [
    {
      "id": 1,
      "name": "Python 코드 리뷰",
      "type": "regression",
      "input": "Review this code: def add(a,b): return a+b",
      "expected_output": "The function is correct but lacks type hints and docstring.",
      "criteria": "Must identify missing type hints. Must not be sycophantic."
    },
    {
      "id": 2,
      "name": "보안 취약점 분석",
      "type": "improvement",
      "input": "Analyze this for security issues: query = f'SELECT * FROM users WHERE id={user_id}'",
      "expected_output": "SQL injection vulnerability detected.",
      "criteria": "Must identify SQL injection. Must suggest parameterized query as fix."
    }
  ]
}
```

### Autopilot 모드: 스캔 → 수정 → 평가 자동 반복

scan, fix, eval을 자동으로 반복하며, eval을 통과하면 종료합니다.

```bash
uv run python main.py autopilot --target haiku-4.5 ./my-project
```

**전제 조건:**
- `eval_cases.json`이 프로젝트 디렉토리에 있어야 합니다
- **regression 타입의 테스트 케이스가 반드시 포함되어야 합니다** (아래 type 설명 참고)

**실행 플로우:**

```
[1/3] Scanning...     → 7 issues found
[1/3] Fixing...       → 7 fixes applied
[1/3] Evaluating...   → 1 regression failed (JSON formatting)
[2/3] Scanning...     → 1 issue found
[2/3] Fixing...       → prompt instruction added
[2/3] Evaluating...   → all passed
Done. 2 iterations.
```

최대 반복 횟수를 지정할 수 있습니다 (기본값: 3):

```bash
uv run python main.py autopilot --target sonnet-4.6 --max-iterations 5 ./my-project
```

## 리포트

모든 리포트는 `report/` 디렉토리에 타임스탬프와 함께 저장됩니다:

```
report/
├── scan_haiku-45_20260406_163000.md     # 스캔 리포트
└── eval_haiku-45_20260406_163500.md     # eval 리포트
```

## 고객이 준비해야 할 것

### 필수
- **코드 디렉토리**: Claude API를 사용하는 프로젝트 코드가 있는 디렉토리 경로
- **타겟 모델**: 마이그레이션할 목표 모델 (haiku-4.5, sonnet-4.5, sonnet-4.6, opus-4.6)

### 권장
- **프롬프트 파일**: 시스템 프롬프트가 별도 파일로 관리되고 있다면, 코드 디렉토리에 포함시키면 에이전트가 함께 분석합니다
- **eval_cases.json**: eval 모드 사용 시 필요. 위의 작성 가이드 참고

## 프로젝트 구조

```
claude-migration-agent/
├── main.py                     # CLI 엔트리포인트 (scan / guide / eval)
├── .env.example                # API 키 템플릿
├── .gitignore
├── setup/                      # uv 환경 설정
│   ├── pyproject.toml          # 의존성 정의
│   ├── create-uv-env.sh        # 환경 셋업 스크립트
│   └── .python-version         # Python 3.12
├── src/
│   └── prompts/                # 에이전트 프롬프트
│       ├── scanner.md          # 스캔 모드 프롬프트
│       ├── fixer.md            # 수정 모드 프롬프트
│       ├── guide.md            # 가이드 모드 프롬프트
│       ├── evaluator.md        # eval 모드 프롬프트
│       └── template.py         # 프롬프트 로더
├── report/                     # 스캔/eval 리포트 저장
├── .claude/skills/             # 마이그레이션 지식
│   ├── migrate-to-haiku-45/    # 12개 항목
│   ├── migrate-to-sonnet-45/   # 12개 항목
│   ├── migrate-to-sonnet-46/   # 19개 항목
│   └── migrate-to-opus-46/     # 26개 항목
│       ├── SKILL.md            # 마이그레이션 체크리스트
│       └── references/         # 참고 자료
└── test-project/               # 테스트용 샘플 코드
```

## 참고 리소스

- [공식 마이그레이션 가이드](https://platform.claude.com/docs/en/about-claude/models/migration-guide)
- [프롬프팅 베스트 프랙티스](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
- [Prompt Improver](https://console.anthropic.com) — Anthropic Console에서 무료 사용 가능 (1-2분)
