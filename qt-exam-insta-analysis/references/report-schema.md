# report.json 스키마 — build_report.py 입력 (단일 데이터 원천)

렌더러(`scripts/build_report.py`)는 이 JSON 하나만 읽어 A4 PDF 를 만든다.
디자인은 `assets/report.css`. 색은 `meta.accent` 한 색만 쓴다(인쇄 친화).

```jsonc
{
  "meta": {
    "academy": "○○영어학원",          // 선택. 헤더 킥커 + 페이지 하단 (실제 학원명으로 교체)
    "teacher": "○○T",                 // 선택. 헤더 킥커
    "accent":  "#1E2A78",             // 선택. 악센트 색(기본 네이비). 제목·표 헤더·강조에만 사용
    "title":   "○○중 2학년 1학기 기말 영어 상세 분석",   // 필수. 리포트 제목
    "date":    "2026.6.30",           // 선택
    "total_questions": 30,            // 선택
    "total_score": 100                // 선택
  },
  "sections": [ /* 아래 타입들을 원하는 순서로. page_break: true 를 주면 그 섹션 앞에서 쪽나눔 */ ]
}
```

## 섹션 타입 (권장 순서대로)

### overview — 총평 (한 문단)
```jsonc
{ "type": "overview", "title": "총평",
  "body": "어법 40점에 변별력이 집중된 시험이다. 특히 …" }
```

### score_table — 유형별 배점 분석
```jsonc
{ "type": "score_table", "title": "유형별 배점 분석",
  "rows": [ { "label": "어법(문법)", "nums": "4·9·10·17·…", "count": 11, "score": 40 } ],
  "footer": { "label": "합계", "nums": "", "count": 30, "score": 100 } }
```

### question_table — 문항 전수 분석표 (이 리포트의 핵심 ①)
**모든 문항**을 한 줄씩. `diff` 는 0~3(★ 개수), `source` 는 출제 근거(교과서 몇 과 본문/어휘표/문법 등).
```jsonc
{ "type": "question_table", "title": "문항 전수 분석표 (30문항)",
  "rows": [
    { "no": 1, "score": 3, "qtype": "어휘", "source": "4과 어휘표(다의어)",
      "diff": 2, "note": "보기 빈칸 어디에도 못 들어갈 단어 — spot 다의어 함정." }
  ] }
```

### transform_table — 교과서 원문 대비 변형 분석 (핵심 ②)
발견된 변형을 **전수**로 적는다. 바뀐 부분은 `[[ ]]` 로 감싼다(원문=빨간 취소선, 시험=강조).
```jsonc
{ "type": "transform_table", "title": "교과서 원문 대비 변형 분석",
  "rows": [
    { "no": 9,
      "before": "balls [[came out]] during the 1970 World Cup",
      "after":  "balls [[have come out]] during the 1970 World Cup",
      "point":  "과거 → 현재완료 (during+과거시점과 충돌)" }
  ] }
```

### deep — 문항별 상세 해설 (핵심 ③)
고난도·변별 문항을 골라 깊게. `crop` 은 출력 PDF 와 같은 폴더 기준 상대경로(모자이크/표기제거 완료본).
`analysis`(왜 이렇게 냈나·정답 근거) / `trap`(학생이 어떻게 틀리나) / `tip`(처방) 세 줄 구조.
```jsonc
{ "type": "deep", "title": "고난도 문항 상세 해설",
  "items": [
    { "no": 1, "score": 3, "title": "다의어 'spot'의 함정",
      "crop": "crops/q1_wide.png",
      "analysis": "시험범위 어휘 학습지의 다의어가 그대로 출제됐다. record·complex·expect·last는 …",
      "trap": "spot을 '발견하다' 하나로만 외운 학생은 …",
      "tip": "다의어는 뜻별 예문과 영영 정의를 함께 정리한다." }
  ] }
```

### mapping — 시험범위 → 출제 매핑
```jsonc
{ "type": "mapping", "title": "시험범위 → 출제 매핑",
  "rows": [ { "topic": "현재완료 (since/for)", "questions": "4·9·17·20·25·29", "note": "본문 어법으로 반복 출제" } ] }
```

### strategy — 다음 시험 대비 전략 (학교 맞춤)
```jsonc
{ "type": "strategy", "title": "다음 시험 대비 전략",
  "items": [ { "title": "현재완료는 '본문 어법'으로 나온다", "body": "교과서 본문을 현재완료↔과거로 바꿔 …" } ] }
```

## 작성 규칙
- 문구는 **완결된 평서문**(개조식 "~함" 금지). 한 덩어리 구절이 줄 끝에서 쪼개질 것 같으면 `\n` 수동 줄바꿈.
- `deep.analysis/trap` 은 보조자료(본문·어휘표·정답)의 **구체적 근거를 인용**. 동어반복·당연한 말 금지.
- 표가 길어 페이지를 넘겨도 된다(표 헤더 자동 반복, 행 단위 쪽나눔 방지 적용).
- 섹션 순서 권장: overview → score_table → question_table → transform_table → deep → mapping → strategy.
