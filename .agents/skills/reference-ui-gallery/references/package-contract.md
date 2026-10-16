# 레퍼런스 항목 계약

항목은 갤러리 checkout의 `references/<slug>/`에 둔다. slug는 소문자 영문/숫자/하이픈 한 경로 조각이다. 기존 항목을 먼저 읽고 새 추출 결과를 병합한다.

| 파일 | 정본 역할 |
|---|---|
| `DESIGN.md` | 디자인 원칙, 구성과 사용 규칙, 상태/반응형/모션/접근성, 플랫폼별 차이 |
| `tokens.json` | 수치와 참조 관계. DTCG 형식의 `$value`, `$type`, `$description` 사용 |
| `reference.json` | 출처, 근거 분류, 플랫폼/태그, 프로토타입 실행법, 검증과 공개 범위 |
| `index.html` | 갤러리에서 여는 미리보기. 복잡한 데모는 정적 진입점과 실행법 제공 |
| `assets/` | 해당 항목에서 사용하는 자산과 필요한 비교 근거. 필요한 경우 생성 |
| `prototype/` | 단일 HTML로 검증하기 어려울 때만 두는 실제 프로토타입 소스 |

## 작성

1. `new <slug> --title <title> --source <source> --platform <platform>`을 실행한다. [디자인 문서 템플릿](../assets/design-template.md), [메타데이터 템플릿](../assets/reference-template.json), [토큰 템플릿](../assets/tokens-template.json)으로 초안을 만든다. 미리보기와 검증 완료 기록은 자동 생성하지 않는다.
2. `DESIGN.md`의 작성 표시를 실제 규칙으로 채운다. 값은 토큰 이름으로 참조하고 HTML과 문서에 독립된 수치 사본을 유지하지 않는다.
3. `tokens.json`에 색상/간격/글꼴/표면/모션 값을 기록한다. 교환 규격이 직접 표현하지 않는 효과는 문서와 이름을 붙인 확장 데이터로 설명한다.
4. `reference.json`의 `sources`와 `evidence`를 채운다. 코드 선언, 화면 측정, 추론, 제안을 같은 확실성으로 쓰지 않는다.
5. 스택과 선택 이유, 실행 명령, 미리보기 진입점을 기록한다. 정적 미리보기에서 확인할 수 없는 네이티브 동작은 별도 실행 검증이나 영상으로 표시한다.

## 메타데이터 예시

`reference-template.json`의 키를 유지하고 실제 값으로 채운다. 증거의 `source_id`는 `sources[].id`를 가리킨다. `locator`에는 선택자/파일 위치/화면 영역처럼 재확인할 위치를 적는다.

```json
{"kind":"measured","source_id":"source-1","locator":"sidebar, desktop viewport","finding":"패널 폭을 고정한 상태에서 측정함"}
```

검증의 `evidence`는 항목 폴더 안의 상대 파일 경로 배열이다. 원본 앱의 개인 경로나 계정 데이터는 공개 메타데이터로 쓰지 않는다.

## 검증

- 원본에 충실한 대표 화면을 같은 조건에서 나란히 비교한다. 의도적으로 바꾼 부분과 오차를 구분한다.
- 추출 때 없던 새 화면 하나를 같은 문법으로 구현한다. 대화 화면에서 추출했다면 설정/검색 결과 화면 등으로 재사용성을 확인한다.
- 관련 컴포넌트의 기본/hover/focus/disabled와 작업의 빈 상태/로딩/오류를 실제로 조작한다. 해당 없는 상태는 이유를 기록한다.
- 좁은 화면과 넓은 화면에서 콘텐츠/포커스/패널 관계를 확인한다. 플랫폼에 없는 반응형 동작은 적용 불가 이유를 기록한다.
- 효과/모션/대비와 키보드 접근을 확인한다. 시각적 충실도와 접근성 조정을 구분한다.

`verification`의 각 항목은 `pass`, `fail`, `not-run`, `not-applicable` 중 하나로 기록한다. `pass`에는 실제 확인 기록 파일을 연결하고, `not-applicable`에는 이유를 적는다. `new_screen`과 `visual`은 준비 완료에 필수다.

`validate --ready`가 통과한 뒤 `status`를 `ready`로 바꾼다. 이 검사는 필수 파일, 로컬 경로, 기본 토큰 타입/참조, 근거와 검증 기록의 완결성을 검사한다. 전체 DTCG 적합성이나 시각 품질은 증명하지 않는다.

기본 검사기는 중괄호 토큰 별칭을 지원한다. JSON Pointer의 `$ref`와 그룹 `$extends`는 지원하지 않으므로 해당 형식이 필요하면 전체 DTCG 검증 도구를 선택하고 검사기를 확장한 뒤 사용한다.

## 변경

새 증거가 기존 토큰을 바꾸면 문서/프로토타입의 소비 지점을 함께 갱신한다. 관련 검증 기록을 `not-run`으로 되돌리고 다시 확인한다. 과거의 `pass` 기록으로 변경된 결과를 완료 처리하지 않는다.

## 공개 파일과 CSS 생성

공개할 때 publication.files에 항목 기준 상대 파일 경로 배열을 넣는다. 미리보기, DESIGN.md, tokens.json, reference.json, 썸네일과 연결된 검증 근거를 포함한다. 목록 밖 파일은 내보내지 않는다.

웹 미리보기에서 토큰 CSS가 필요하면 prototype.token_css에 생성 경로를 적는다. 해당 CSS는 수동 입력 파일로 두지 않는다. 빌더가 토큰의 `$extensions.reference-ui.css_name`과 `theme`(base/light/dark)를 읽어 생성한다. 현재 CSS 출력은 primitive 색상(srgb/oklch/oklab), dimension, duration, fontFamily, fontWeight, number와 별칭을 지원한다. 다른 플랫폼은 그 프로젝트의 변환 도구를 선택한다.
