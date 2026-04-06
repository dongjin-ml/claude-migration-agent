#!/bin/bash

# UV 환경 설정 및 Jupyter 커널 등록 스크립트 (pyproject.toml 기반)
# 사용법: ./create-uv-env.sh <환경이름> [python버전]

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

usage() {
    echo "사용법: $0 <환경이름> [python버전]"
    echo ""
    echo "예시:"
    echo "  $0 myproject"
    echo "  $0 myproject 3.12"
    echo ""
    echo "옵션:"
    echo "  환경이름     : 생성할 환경의 이름 (필수)"
    echo "  python버전   : 사용할 Python 버전 (선택, 기본값: 3.12)"
    exit 1
}

if [ $# -lt 1 ]; then
    print_error "환경 이름이 필요합니다."
    usage
fi

ENV_NAME=$1
PYTHON_VERSION=${2:-3.12}
VENV_PATH=".venv"

print_info "환경 설정을 시작합니다..."
print_info "환경 이름: $ENV_NAME"
print_info "Python 버전: $PYTHON_VERSION"
print_info "가상 환경 경로: $VENV_PATH"

# 기존 가상환경 정리
if [ -d "$VENV_PATH" ]; then
    print_warning "기존 가상환경을 제거합니다: $VENV_PATH"
    rm -rf .venv
    print_success "기존 가상환경이 제거되었습니다."
fi

# UV 설치 확인 및 자동 설치
install_uv() {
    print_info "UV를 설치합니다..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

    if [ -f "$HOME/.local/bin/env" ]; then
        source "$HOME/.local/bin/env"
    fi

    if command -v uv &> /dev/null; then
        print_success "UV가 성공적으로 설치되었습니다!"
        uv --version
    else
        print_error "UV 설치에 실패했습니다."
        print_info "수동 설치 방법:"
        echo "  1. 공식 스크립트: curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo "  2. pip: pip install uv"
        echo "  3. pipx: pipx install uv"
        exit 1
    fi
}

if ! command -v uv &> /dev/null; then
    print_warning "UV가 설치되어 있지 않습니다."
    read -p "UV를 자동으로 설치하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_uv
    else
        print_error "UV가 필요합니다. 수동으로 설치해주세요."
        exit 1
    fi
fi

# 1. Python 버전 설정
print_info "Python $PYTHON_VERSION 설정 중..."
uv python pin $PYTHON_VERSION
print_success "Python $PYTHON_VERSION이 설정되었습니다."

# 2. 프로젝트 초기화
print_info "프로젝트 초기화 중..."
if [ ! -f "pyproject.toml" ]; then
    uv init --name "$ENV_NAME"
    print_success "프로젝트가 '$ENV_NAME'으로 초기화되었습니다."
else
    print_warning "이미 pyproject.toml이 존재합니다. 기존 프로젝트를 사용합니다."
fi

# 3. 필수 패키지 추가
print_info "Jupyter 관련 필수 패키지 추가 중..."
uv add ipykernel jupyter

# 4. pyproject.toml 확인 및 의존성 설치
if [ -f "pyproject.toml" ]; then
    print_info "pyproject.toml 발견. 의존성 동기화 중..."
    uv sync
    print_success "pyproject.toml 기반으로 의존성이 설치되었습니다."
else
    print_error "pyproject.toml이 없습니다."
    exit 1
fi

# 5. Jupyter 커널 등록
print_info "Jupyter 커널 등록 중..."
DISPLAY_NAME="$ENV_NAME (UV)"

if jupyter kernelspec list 2>/dev/null | grep -q "$ENV_NAME"; then
    print_warning "기존 '$ENV_NAME' 커널을 제거합니다..."
    jupyter kernelspec remove -f "$ENV_NAME" || {
        print_warning "커널 제거 실패, 계속 진행합니다..."
    }
fi

uv run python -m ipykernel install --user --name "$ENV_NAME" --display-name "$DISPLAY_NAME" || {
    print_error "Jupyter 커널 등록에 실패했습니다."
    exit 1
}
print_success "Jupyter 커널이 '$DISPLAY_NAME'로 등록되었습니다."

# 6. 설치 확인
print_info "설치 확인 중..."
echo ""
echo "=== 설치된 Python 버전 ==="
uv run python --version

echo ""
echo "=== 설치된 패키지 목록 ==="
uv pip list

echo ""
echo "=== 등록된 Jupyter 커널 ==="
jupyter kernelspec list 2>/dev/null | grep -E "(Available|$ENV_NAME)" || echo "커널 목록을 가져올 수 없습니다."

# 7. 루트 디렉토리에 환경 파일 연결 (심링크 생성)
print_info "루트 디렉토리에 UV 환경 파일 연결 중..."
cd ..

for file in pyproject.toml .venv uv.lock; do
    if [ -e "$file" ] && [ ! -L "$file" ]; then
        print_warning "기존 $file 파일을 ${file}.backup으로 백업합니다."
        mv "$file" "${file}.backup"
    elif [ -L "$file" ]; then
        print_info "기존 심링크 $file를 제거합니다."
        rm "$file"
    fi
done

ln -s setup/pyproject.toml . || {
    print_error "pyproject.toml 심링크 생성 실패"
    exit 1
}

ln -s setup/.venv . || {
    print_error ".venv 심링크 생성 실패"
    exit 1
}

if [ -f "setup/uv.lock" ]; then
    ln -s setup/uv.lock . || {
        print_warning "uv.lock 심링크 생성 실패"
    }
fi

print_success "루트 디렉토리에 UV 환경 파일이 연결되었습니다!"

echo ""
print_success "환경 설정이 완료되었습니다!"
echo ""
echo "=== 사용 방법 ==="
echo "1. 패키지 추가: uv add <패키지명>"
echo "2. 패키지 제거: uv remove <패키지명>"
echo "3. 의존성 동기화: uv sync"
echo "4. 스크립트 실행: uv run python main.py (루트에서 실행 가능!)"
echo "5. Jupyter Lab 실행: uv run jupyter lab"
echo "6. 새 노트북 생성 시 '$DISPLAY_NAME' 커널 선택"
echo ""
print_info "이제 루트 디렉토리에서 'uv run python main.py' 실행이 가능합니다!"
print_info "전통적인 방식으로 활성화: source .venv/bin/activate"
print_info "UV 권장 방식: uv run <명령어>"
