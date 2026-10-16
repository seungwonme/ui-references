# UI References

웹과 앱의 UI를 분석해 디자인 규칙, 토큰, 실행 가능한 프로토타입으로 보관하는 갤러리입니다. 갤러리를 만들고 관리하는 프로젝트 스킬도 이 저장소에 함께 들어 있습니다.

[갤러리 열기](https://seungwonme.github.io/ui-references/) / [프로젝트 스킬](.agents/skills/reference-ui-gallery/SKILL.md) / [Aside 디자인 규칙](references/aside-glass/DESIGN.md)

## 프로젝트 스킬

프로젝트 스킬은 `reference-ui-gallery` 하나입니다. 전역 `reference-ui`와 이름이 충돌하지 않도록 호출명을 구분했으며, 본문부터 테스트까지 전체 묶음을 포함합니다.

```text
.agents/skills/reference-ui-gallery/
├── SKILL.md
├── README.md
├── references/    # 설정, 추출, 산출물 계약, 재사용과 발행
├── scripts/       # 생성, 검증, 빌드, GitHub 발행
├── assets/        # 빈 설정, 토큰/메타데이터 템플릿, 갤러리와 Actions
└── tests/         # 행동 검사와 평가 기록

references/<id>/
├── index.html
├── DESIGN.md
├── tokens.json
├── reference.json
└── assets/        # 해당 레퍼런스가 사용하는 공개 자산
```

저장소를 작업 폴더로 연 뒤 다음 이름으로 호출할 수 있습니다.

- Codex: `$reference-ui-gallery`
- Claude Code: `/reference-ui-gallery`
- GJC: `/skill:reference-ui-gallery`

Claude Code의 `.claude/skills/reference-ui-gallery`와 GJC의 `.gjc/skills`는 저장소 안의 정본을 가리키는 상대 링크입니다. Codex는 `.agents/skills/`에서 직접 읽습니다. 실제 사용자 설정과 원본 레퍼런스 자산은 스킬 폴더 밖에 둡니다.

## 로컬 사용

Python 3.10+와 Git이 필요하며, GitHub 발행에는 인증된 `gh`를 사용합니다.

```sh
python3 scripts/gallery.py --help
python3 scripts/gallery.py doctor
python3 scripts/gallery.py catalog --public
python3 scripts/gallery.py build --output ./site-preview
python3 -m http.server --directory ./site-preview
```

명령은 저장소 루트에서 실행합니다. 빌드 출력은 새 폴더나 빈 폴더를 지정합니다. 래퍼가 이 checkout을 직접 선택하므로 개인 설정 파일 없이도 실행할 수 있습니다.

디자인 시스템을 재사용할 때는 글꼴, 의미 색상, 간격과 컴포넌트 규칙을 대상 서비스에 맞게 적용합니다. 원본 사진과 특정 화면 배치는 재현 요청이나 대상 콘텐츠에 필요한 경우에 사용합니다.

## 수정과 발행

레퍼런스의 값은 `tokens.json`, 사용 규칙은 `DESIGN.md`, 출처와 검증 범위는 `reference.json`에서 관리합니다. 갤러리 자체의 테마는 루트 `gallery.css`에 있습니다.

```sh
python3 scripts/gallery.py validate <id> --ready --public
python3 scripts/gallery.py publish references/<id>
python3 scripts/gallery.py publish references/<id> --apply
```

기본 `publish`는 계획만 출력합니다. `--apply`는 별도 worktree에서 공개 파일과 전체 스킬 묶음을 준비하고 PR과 CI 빌드까지 진행합니다. 리뷰 후 머지까지 승인된 작업에는 `--merge`를 추가할 수 있으며, Actions 배포와 실제 Pages의 커밋을 확인합니다. 중단된 발행은 `finish --pr <number> --entry <id> --apply`로 이어갈 수 있습니다.

루트 래퍼는 프로젝트 스킬의 코드를 우선 실행합니다. `.reference-ui/`는 호환 런타임과 생성 파일의 버전/hash 기록을 담습니다. 발행 스크립트가 프로젝트 묶음과 런타임을 같은 원본으로 갱신하므로 생성 사본을 각각 편집할 필요가 없습니다.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .agents/skills/reference-ui-gallery/tests
```
