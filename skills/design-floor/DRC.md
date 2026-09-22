# `mockTech` rule catalogue

`mockDrcCheck(cv)` returns a list of violation strings for one cellview, or an
empty list. The codes below are **this session's own**. They imitate the shape
of industry names without being them, so this file is the only place their
meaning lives — do not infer a rule from its code.

```
mockDrcCheck(dbOpenCellViewByType("STDLIB" "INV" "layout" "maskLayout" "r"))
```

## Codes

| 코드 | 심각도 | 검사 | 위반 시 의미 · 전형적 수정 |
|---|---|---|---|
| DRC-WIDTH-001 | error | 도형의 짧은 변이 레이어 최소 폭 이상 | 너무 가는 배선·확산 — 폭을 키우거나 두 개로 쪼갠 도형을 하나로 합친다 |
| DRC-SPACE-001 | error | 같은 레이어 두 도형의 간격이 최소 간격 이상 | 붙지도 겹치지도 않은 채 너무 가까움. **맞닿거나 겹친 도형은 위반이 아니다** — 한 덩이의 금속이고, 이걸 위반이라 부르면 체커가 꺼진다 |
| DRC-GRID-001 | error | 모든 좌표가 제조 그리드(0.005 µm) 위 | 생성된 레이아웃에서 가장 흔함. 좌표를 그리드에 반올림 |
| DRC-AREA-001 | warn | 도형 면적이 레이어 최소 면적 이상 | 폭은 맞지만 너무 짧은 조각 — 길이를 늘리거나 제거 |

최소치에 **정확히** 맞춰 그린 도형은 합법이다. `x1 - x0`는 이진 부동소수점이
허용하는 만큼만 정확해서, 0.14 µm met1 배선이 시작할 수 있는 2001개 그리드 위치 중
919개가 0.13999999999999999로 빼진다. 그래서 모든 최소치 비교에 1e-9 µm의 여유를
둔다 — 그리드(5e-3)보다 한참 아래이고 표현 오차(~1e-16)보다 한참 위다. 이 여유가
없으면 최소폭 도형의 절반이 위반으로 찍히고, 그게 체커가 꺼지는 가장 빠른 길이다.

`error` 셋은 실제 공정이라면 마스크를 만들 수 없는 것들이고, `DRC-AREA-001`만
`warn`이다. 이 세션은 위반이 있어도 **빌드를 막지 않는다** — 무엇이 지어졌는지와
그것이 규칙을 지키는지는 별개의 사실이고, 둘을 합치면 어느 쪽도 읽을 수 없다.

## 레이어별 최소값 (µm, 면적은 µm²)

| 레이어 | width | space | area |
|---|---|---|---|
| nwell | 0.840 | 1.270 | 0.700 |
| diff | 0.150 | 0.270 | 0.045 |
| poly | 0.150 | 0.210 | 0.030 |
| met1 | 0.140 | 0.140 | 0.083 |
| met2 | 0.140 | 0.140 | 0.067 |
| met3 | 0.300 | 0.300 | 0.240 |

`text`는 주석이고 물리적 크기가 없어서 표에 **없다** — 0을 넣으면 "검사해서
통과했다"로 읽히기 때문이다. 표에 없는 레이어는 그리드 검사도 받지 않는다:
`text`는 제조되지 않으므로 그리드를 벗어난 라벨 좌표는 고칠 것이 없는 위반이다.

## 이 체크가 증명하지 않는 것

사인오프가 아니다. Assura도 PVS도 아니고, 위 숫자는 어느 파운드리에서도
가져오지 않은 이 mock 자신의 값이다. 깨끗한 결과는 **이 규칙들을** 지켰다는
증거이고 그 이상이 아니다. 특히 검사하지 **않는** 것:

- enclosure, 즉 via를 금속이 얼마나 덮는지
- antenna, density, well tie, latch-up
- 인스턴스 **내부** — master를 검사할 때 검사된다. 배치할 때마다 같은 위반을
  다시 찍으면 고쳐야 할 한 곳이 묻힌다
- 서로 다른 레이어 사이의 어떤 관계도

`mockDrcCheck`가 실행되지 못하면 결과는 `NOT CHECKED — <이유>`다. 실행하지 못한
검사는 통과한 검사가 아니다 — `roles/verify.md`와 같은 규율이다.
