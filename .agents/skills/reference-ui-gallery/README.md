# reference-ui-gallery

원본 UI를 디자인 규칙과 토큰, 실행 가능한 프로토타입으로 정리해 외부 갤러리 저장소에 보관하는 공용 workflow 스킬이다. 화면 제작만 하는 frontend 스킬이나 시각 QA 스킬과 달리 추출 근거, 디자인 시스템 정본, 새 화면 재사용 검증의 연결을 맡는다.

사용자 진입점은 [SKILL.md](SKILL.md)다. 도구는 Python 표준 라이브러리, Git, GitHub CLI를 사용한다. 설정/조회/검증/빌드는 로컬에서 실행한다. 저장소 생성과 발행은 먼저 계획을 반환하고 `--apply`에서만 외부 변경을 실행한다. 사용자 설정은 설치 폴더 밖에 두고, 배포 템플릿의 사용자 값은 비워 둔다.

## 설계 근거

| 출처 | 반영한 원칙 |
|---|---|
| [Agent Skills 규격](https://agentskills.io/specification) | 공통 frontmatter와 단계별 참조. 사용자 설정 로더는 별도로 구현. |
| [XDG 설정 경로](https://specifications.freedesktop.org/basedir/latest/) | 사용자 설정과 설치 코드를 분리. |
| [Git remote](https://git-scm.com/docs/git-remote) | 현재 원격은 Git으로 조회하고 복원 주소와 구분. |
| [gstack 복원 구현](https://github.com/garrytan/gstack/blob/953a62a72412ba2ec430972226b7b3a999839df5/bin/gstack-brain-restore) | 설치 폴더 밖에 복원용 URL을 보존하는 선례. 구현 코드는 복사하지 않음. |
| [DTCG 토큰 형식](https://www.designtokens.org/tr/2025.10/format/) | 도구/플랫폼과 분리한 토큰 값과 참조. 헬퍼는 기본 구조만 검사. |
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

[테스트](tests/test_reference_ui.py)는 설정 격리, 기존 데이터 보존, 경로 이탈, 토큰 참조, 준비/공개 게이트를 확인한다. `python3 -m unittest discover -s tests`로 실행한다. [경량 평가](tests/eval-cases.json)는 명확한 호출, 다른 표현, near-miss와 on/off 비교에 사용한다.

초기 후보의 관찰 결과와 한계는 [경량 평가 기록](tests/eval-report.md)에 있다.

스킬 변경은 skill-manager의 portable/authoring/description/reference 검사와 새 컨텍스트 평가를 거친다. 설치/발견/명시 호출/자동 선택의 결과는 런타임별로 구분한다. 릴리스 버전은 SKILL.md의 metadata에 있다.
