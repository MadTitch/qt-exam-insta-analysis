# deck.json 스키마 — build_cards.py 입력 (단일 데이터 원천)

렌더러(`scripts/build_cards.py`)는 이 JSON 하나만 읽는다. 디자인은 `assets/base.css`(공통)
+ `assets/theme_a~i.css`(테마), 치수/색/폰트 규칙은 `references/design-spec.md` 가 단일 원천이다.

```jsonc
{
  "brand": {
    "academy": "○○영어학원",            // 필수. 워터마크/마무리에 들어감 (실제 학원명으로 교체)
    "teacher": "○○T",                   // 선택. 표지/마무리. 없으면 생략 (실제 강사명으로 교체)
    "palette": "navy",                  // 색 조합 프리셋 이름(권장). sunset/navy/ocean/teal/forest/plum/berry/rose/gold/slate
    "color":   "#3B4FD8",               // palette 없을 때만 사용하는 단색(여기서 톤 파생). palette 가 우선
    "style":   "A",                     // 선택. 디자인 테마 A~I (없으면 A). 색과 독립. 4단계 --samples 로 고른 값
    "title":   "○○중2 영어분석",         // 표지 제목(학교+학년+과목)
    "subtitle":"26학년도 1학기 기말고사",  // 표지 부제
    "hashtags":["#객관식", "#서술형", "#모두잡기"],
    "slogan":  "실수는 줄이고 실력은 높이고!"
  },
  "cards": [ /* 순서대로 렌더 = 인스타 캐러셀 순서. 표지 포함 최대 20장 */ ]
}
```

## 카드 타입

표지/마무리를 뺀 모든 카드는 공통으로 `"tab"`(폴더 탭 라벨, 선택)을 가질 수 있다.

### cover (표지)
```jsonc
{ "type": "cover" }   // brand.title / subtitle / teacher 를 사용. 추가 필드 불필요
```

### scope (시험범위·문법 토픽)
```jsonc
{ "type": "scope", "tab": "시험범위 문법 토픽",
  "heading": "동아(윤) 영어2  1,2과",
  "items": ["간접의문문", "to부정사의 형용사적 용법", "분사구문"] }
```

### score_table (유형별 배점표)
```jsonc
{ "type": "score_table", "tab": "출제 유형별 배점 분석",
  "heading": "유형별 문항·배점",
  "rows": [
    { "label": "독해",   "nums": "4,5,6,7", "score": 51 },
    { "label": "대화문", "nums": "8,9",     "score": 8 }
  ],
  "footer": { "label": "합계", "nums": "총 30문항", "score": 100 } }
```
- `score` 가 빈 문자열이면 점수 칸을 비운다.

### feature_list (영역별 출제 특징)
```jsonc
{ "type": "feature_list", "tab": "영역별 출제 특징 상세",
  "heading": "영역별 특징",
  "items": [
    { "title": "독해: 압도적 비중",
      "body": "영어 선지 객관식으로, 지문의 세부 정보를 정확히 확인했는지를 집중적으로 물었다." }
  ] }
```
- `body`/`title`은 **완결된 평서문**으로(개조식 "~함" 금지). 한 덩어리로 읽혀야 하는 구절이 줄
  끝에서 쪼개질 것 같으면 문자열에 `\n`을 넣어 직접 줄을 나눈다(렌더러가 `<br>`로 변환).

### deep_dive (문항 심층분석 — 크롭 이미지 1장 + 설명)
```jsonc
{ "type": "deep_dive", "tab": "문항 심층분석 1",
  "title": "어휘 - 영영풀이의 함정",
  "crop": "crops/q14.png",   // 출력 폴더(=2번째 인자) 기준 상대경로. crop_question.py 가 만든 (모자이크 완료) PNG
  "body": "시험범위 어휘표의 영영풀이가 그대로 선지로 나온 문항이다. 뜻을 알아도 정의 문장을\n해석하지 못하면 틀리기 때문에, 다의어를 한 가지 뜻으로만 외운 학생이 특히 약하다." }
```
- `crop` PNG 는 **이미 모자이크/표기제거가 된** 상태여야 한다. 렌더러는 추가 처리를 하지 않는다.
- `body`는 **"학생이 왜 틀리는가"**를 보조자료(본문·어휘표·정답)의 구체적 근거로 쓴다. 동어반복 금지.

### transform (교과서 원문 → 시험 변형 · before→after)
```jsonc
{ "type": "transform", "tab": "교과서 → 시험, 이렇게 바꿨다",
  "heading": "원문을 비틀어 만든 어법 함정",
  "rows": [
    { "before": "balls [[came out]] during the 1970 World Cup",
      "after":  "balls [[have come out]] during the 1970 World Cup",
      "point":  "과거 → 현재완료 (during+과거시점과 충돌)" }
  ] }
```
- 원본 지문 보조자료가 있을 때 만든다. 원문↔시험 문장을 나란히 보여주고 바뀐 지점을 짚는다.
- **바뀐 부분은 `[[ ]]`로 감싼다** → 원문은 빨간 취소선, 시험은 강조(밑줄)로 렌더된다.
- `point`(선택)은 변형 유형 한 줄. **한 카드에 3행 이하**(넘치면 잘린다). 많으면 카드를 나눈다.

### strategy (대비 전략)
```jsonc
{ "type": "strategy", "tab": "대비 전략은??",
  "heading": "다음 기말고사 대비 전략",
  "items": [ { "title": "조건부 영작 연습", "body": "..." } ] }
```

### outro (마무리·브랜드)
```jsonc
{ "type": "outro" }   // brand.slogan / hashtags / academy 를 사용
```

## 옵션 카드
난이도·변별 분포 / 객관식 vs 서술형 비중 / 오답 유발 장치 모음 / 출제경향 변화 등은
별도 타입을 만들지 말고 `feature_list`(서술형) 또는 `score_table`(수치형)을 재활용한다.

## 검증
- `cards` 길이는 **표지+마무리 포함 20 이하** (인스타 캐러셀 한도). build_cards.py 가 초과 시 경고.
- 모든 `deep_dive.crop` 파일은 출력 폴더 기준으로 실제 존재해야 한다(없으면 에러).
