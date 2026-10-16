# 설정과 저장소 연결

현재 작업이 갤러리 저장소 안이고 루트에 `scripts/gallery.py`가 있으면 그 래퍼를 실행한다. 이 진입점은 저장소 경로를 직접 전달하므로 다른 갤러리를 가리키는 개인 설정을 읽지 않는다.

그 외에는 현재 스킬 경로의 `scripts/reference-ui.py`를 실행한다. 옵션은 `--help`에서 확인하고 설정 파일의 값은 스킬 문서에 복제하지 않는다.

## 설정 소유권

- 설정 위치는 명시한 `--config`가 우선이다. 생략하면 `XDG_CONFIG_HOME` 아래 `reference-ui/config.json`, 해당 환경변수가 없으면 홈의 `.config/reference-ui/config.json`을 사용한다.
- [빈 설정 예시](../assets/config.example.json)는 배포용이다. 사용자 설정은 `config init`으로 생성하고 `config set`으로 수정한다.
- `workspace_path`는 사용자가 고른 갤러리 Git checkout이다. 새 경로가 필요하면 `~/.ui-references`를 제안하되 기존 갤러리가 있으면 재사용한다.
- `bootstrap_url`은 처음 복제하거나 복원할 주소다. 빈 값이면 로컬 저장소만 사용할 수 있다. 인증정보를 포함한 URL은 저장하지 않는다.
- `remote_name`은 현재 저장소에서 읽을 Git remote 이름이다. 기본값은 `origin`이다.
- 설정은 JSON으로 파싱한다. 파일 누락과 잘못된 JSON을 구분하며, 오류가 나면 다른 기본 경로에 새 갤러리를 만들지 않는다.

## 처음 연결할 때

1. 같은 갤러리를 담은 저장소가 있는지 확인한다. 경로와 원격은 기존 대화에서 지정한 값을 재사용한다.
2. 새 GitHub 갤러리는 `setup-gallery --repo <owner/repository> --directory <checkout> --visibility <public|private>`로 계획을 확인하고, 요청 범위가 맞으면 `--apply`로 생성/복제와 외부 설정을 함께 처리한다. 기존 저장소의 공개 범위를 바꾸거나 다른 checkout을 덮어쓰지 않는다.
3. 이미 있는 로컬 checkout만 연결할 때는 `config init --workspace <checkout>`을 실행한다. 이 명령은 설정만 쓴다. CI에서는 `--workspace <checkout>`을 사용해 사용자 설정을 읽지 않는다.
4. `doctor`를 실행해 Git 루트와 원격의 일치 여부를 확인한다. URL 값은 기본 출력에서 가린다.
5. 출력의 경로와 항목 수가 의도한 갤러리인지 확인한 뒤 항목을 만든다.

## 위치나 원격을 바꿀 때

`config set`은 설정만 바꾼다. 데이터 이동, clone, `git remote set-url`은 해당 요청에 맞게 별도로 수행하고 다시 `doctor`로 확인한다. HTTPS와 SSH의 같은 호스트/저장소 표기는 비교하되 SSH 별칭이나 Git URL 치환을 확인하지 못하면 불일치를 자동 수정하지 않는다.

스킬 업데이트는 이 외부 설정과 갤러리를 보존한다. 빈 템플릿을 사용자 설정 위에 다시 복사하지 않는다.
