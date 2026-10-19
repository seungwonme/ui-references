# reference-ui-gallery

원본 UI를 디자인 규칙과 토큰, 실행 가능한 프로토타입으로 정리해 외부 갤러리 저장소에 보관하는 공용 workflow 스킬이다. 추출 근거, 디자인 시스템 정본, 패키지 안의 새 화면 재사용 검증과 갤러리 홈페이지/테마/발행을 맡는다. 준비된 디자인을 별도 제품에 적용하기만 하는 구현은 해당 제품의 개발 워크플로가 맡는다.

사용자 진입점은 [SKILL.md](SKILL.md)다. 도구는 Python, uv로 고정한 jsonschema 환경, Git, GitHub CLI를 사용한다. 설정/조회/검증/빌드는 로컬에서 실행한다. 저장소 생성과 발행은 먼저 계획을 반환하고 `--apply`에서만 외부 변경을 실행한다. 사용자 설정은 설치 폴더 밖에 두고, 배포 템플릿의 사용자 값은 비워 둔다.

## REA, Taste, prototype 연결

| 역할 | 연결된 절차 |
|---|---|
| REA로 원본 앱/번들/웹에서 구조와 근거 확보 | [대상별 도구, 실제 입력, 토큰/디자인 문서로 정리하는 방법](references/rea-extraction.md) |
| taste-skill로 시각 방향과 개선안 선택 | [웹 아트 디렉션과 앱 개선을 나누는 적용 기준](references/taste-and-prototype.md) |
| Matt Pocock prototype으로 구조 비교 | [같은 화면/데이터로 세 안을 비교하고 결과를 보존하는 절차](references/taste-and-prototype.md#prototype을-공통-비교-절차로-쓰기) |

REA MCP와 Taste/prototype 플러그인은 외부 도구다. 이 패키지는 이들을 선택하고 결과를 연결하는 절차를 포함한다. 설치된 도구/스킬을 먼저 확인하며, 미설치 또는 미실행을 사용 완료로 표시하지 않는다. 프로젝트 스킬을 배포할 때도 위 참조 문서를 전체 묶음에 포함한다.

## 설계 근거

| 출처 | 반영한 원칙 |
|---|---|
| [Agent Skills 규격](https://agentskills.io/specification) | 공통 frontmatter와 단계별 참조. 사용자 설정 로더는 별도로 구현. |
| [XDG 설정 경로](https://specifications.freedesktop.org/basedir/latest/) | 사용자 설정과 설치 코드를 분리. |
| [Git remote](https://git-scm.com/docs/git-remote) | 현재 원격은 Git으로 조회하고 복원 주소와 구분. |
| [gstack 복원 구현](https://github.com/garrytan/gstack/blob/953a62a72412ba2ec430972226b7b3a999839df5/bin/gstack-brain-restore) | 설치 폴더 밖에 복원용 URL을 보존하는 선례. 구현 코드는 복사하지 않음. |
| [DTCG 토큰 형식](https://www.designtokens.org/tr/2025.10/format/) / [공식 스키마](https://www.designtokens.org/schemas/2025.10/format.json) | 로컬 공식 스키마와 처리한 값/별칭 검사를 결합. 지원 프로파일은 [산출물 계약](references/package-contract.md)에 명시. |
| [Google DESIGN.md 규격](https://github.com/google-labs-code/design.md/blob/6e5da5382f41edbba9d73b2c62f33f32e9971f15/docs/spec.md) | 파일 이름과 구조화된 교환 형식을 구분. 기존 산문을 보존하며 Google 호환 내보내기를 자동 주장하지 않음. |
| [DTCG 소스](https://github.com/design-tokens/community-group/tree/882ebd6716abef9a46d8ef5fb12e82009d6cee2e/schemas) / [라이선스](assets/dtcg-license.md) | 수정하지 않은 번들 스키마의 SHA-256을 코드에서 확인. 스키마의 저작권과 라이선스는 원 출처를 따름. |
| [REA](https://github.com/morluto/rea) | 선택 가능한 분석 도구. 정적 분석과 실제 렌더링의 근거 구분. |
| [Matt Pocock skills](https://github.com/mattpocock/skills) | 질문을 정하고 대표 프로토타입으로 비교. 보관을 요청한 결과는 갤러리에 유지. |
| [GitHub Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) | PR 빌드와 main 배포 분리, 최소 Pages/OIDC 권한, 실제 배포 확인. |
| [Taste skill](https://github.com/leonxlnx/taste-skill) | 용도별 선택 적용. 레퍼런스 충실도와 플랫폼 요구를 우선. |

## 자동화

`setup-gallery`는 GitHub 저장소와 외부 설정을 연결한다. `publish`는 검증된 항목의 공개 파일만 새 worktree로 가져와 재현 가능한 빌더와 Actions를 포함한 PR을 만든다. 승인된 `--merge` 실행은 PR 빌드 성공을 확인한 뒤 머지하고, 배포 Actions와 실제 Pages의 commit manifest를 대조한다. 중단되면 `finish`로 기존 PR을 이어간다.

CI의 저장소 래퍼는 프로젝트 스킬이 있으면 그 실행 코드를 사용하고, 없으면 `.reference-ui/` 런타임을 사용한다. 사용자의 홈, 전역 스킬 설치, 인증 파일을 읽지 않는다. 생성물 hash가 달라지면 사용자의 수정으로 보고 업데이트를 멈춘다.

`publish --project-skill`은 이 스킬 전체를 프로젝트의 `.agents/skills/reference-ui-gallery/`에 함께 배포한다. 전역 `reference-ui`와 구분되는 프로젝트 호출명이며, 별도 기능을 가진 새 스킬은 아니다. 실행용 `.reference-ui/`와 프로젝트 묶음은 같은 원본에서 생성하고 하나의 manifest로 검증한다. 한 번 포함한 저장소는 이후 발행에서도 전체 묶음을 갱신한다.

갤러리의 테마는 저장소가 소유하는 `gallery.css`에서 관리한다. 스킬에는 공통 화면과 중립적인 기본값만 두며, 선택한 레퍼런스의 토큰/폰트/배경 연결은 갤러리 저장소에 남는다. [재사용과 갤러리](references/gallery-and-reuse.md)에 연결 방법을 설명한다.

## 유지보수와 검증

[행동 테스트](tests/test_reference_ui.py)와 [토큰 회귀 테스트](tests/test_token_contract.py)는 설정 격리, 기존 데이터 보존, 토큰 타입/상속/별칭과 CSS 변환을 확인한다. [반복 검증 환경](references/package-contract.md#반복-검증-환경)의 `check`가 이 테스트와 실제 패키지/임시 빌드를 함께 실행한다. [경량 평가](tests/eval-cases.json)는 모델의 명확한 호출, 다른 표현, near-miss와 on/off 비교에 사용한다. 자동 회귀 테스트와 모델 평가는 별개다.

초기 후보의 관찰 결과와 한계는 [경량 평가 기록](tests/eval-report.md)에 있다.

0.6.0의 결정론적 검사 범위와 결과는 [토큰 계약 검증](tests/token-contract-report.md)에 있다. 검사에는 [고정한 스키마](assets/dtcg-format.schema.json), [값/별칭 검사 구현](scripts/token-validation.py), [Python 잠금 파일](scripts/reference-ui.py.lock)을 사용한다.

스킬 변경은 skill-manager의 portable/authoring/description/reference 검사와 새 컨텍스트 평가를 거친다. 설치/발견/명시 호출/자동 선택의 결과는 런타임별로 구분한다. 릴리스 버전은 SKILL.md의 metadata에 있다.
