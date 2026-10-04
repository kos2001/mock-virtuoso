/* Shared KO/EN UI localization. Technical data and user inputs are never rewritten. */
(() => {
  const pairs=[
  [
    "언어",
    "Language"
  ],
  [
    "화면 테마",
    "Theme"
  ],
  [
    "시스템",
    "System"
  ],
  [
    "밝게",
    "Light"
  ],
  [
    "어둡게",
    "Dark"
  ],
  [
    "회로 · 시뮬레이션",
    "Circuit · Simulation"
  ],
  [
    "PDK · DRC / LVS",
    "PDK · DRC / LVS"
  ],
  [
    "회로 편집 · ERC · ngspice",
    "Circuit editor · ERC · ngspice"
  ],
  [
    "닫기",
    "Close"
  ],
  [
    "소자의 net 이름으로 연결합니다. 접지는 0, 값은 SI 단위입니다(1 kΩ = 1000, 1 µF = 1e-6). 범용 모델과 SKY130 모델을 선택할 수 있습니다.",
    "Connect terminals by net name. Ground is 0; values use SI units (1 kΩ = 1000, 1 µF = 1e-6). Choose generic or SKY130 models."
  ],
  [
    "시뮬레이터 확인 중…",
    "Checking simulator…"
  ],
  [
    "ngspice 준비됨 · OP / DC / AC / Transient",
    "ngspice ready · OP / DC / AC / Transient"
  ],
  [
    "ngspice 미설치 · ERC와 SPICE 내보내기는 사용 가능합니다.",
    "ngspice is not installed. ERC and SPICE export remain available."
  ],
  [
    "설계 DB에 저장",
    "Save to design DB"
  ],
  [
    "DB에서 불러오기",
    "Load from DB"
  ],
  [
    "JSON 가져오기",
    "Import JSON"
  ],
  [
    "JSON 저장",
    "Export JSON"
  ],
  [
    "SPICE 내보내기",
    "Export SPICE"
  ],
  [
    "분압기 예제",
    "Voltage divider"
  ],
  [
    "DB 저장은 현재 서버의 CIRCUITS 라이브러리에 같은 이름의 회로를 대체합니다. 서버 재시작 후에도 보관하려면 JSON으로 저장하세요.",
    "Saving replaces the circuit with the same name in the server's CIRCUITS library. Export JSON to keep it across server restarts."
  ],
  [
    "1. 회로와 공정 모델",
    "1. Circuit and process model"
  ],
  [
    "2. 소자와 연결",
    "2. Devices and connections"
  ],
  [
    "3. 해석과 실행",
    "3. Analysis and execution"
  ],
  [
    "표준 셀 예제",
    "Standard cell examples"
  ],
  [
    "예제 불러오기",
    "Load example"
  ],
  [
    "학습용 CMOS 회로입니다. 공인 표준 셀 라이브러리의 레이아웃·타이밍 뷰는 포함하지 않습니다. 1.8 V 입력과 5 fF 부하로 모든 입력 조합을 순서대로 실행합니다.",
    "Educational CMOS circuits, without qualified standard-cell layout or timing views. Each testbench cycles through every input combination with 1.8 V inputs and a 5 fF load."
  ],
  [
    "표준 셀 예제를 불러왔습니다. 시뮬레이션 실행 후 입력과 vout 파형을 비교하세요.",
    "Standard cell example loaded. Run the simulation and compare the input and vout waveforms."
  ],
  [
    "SKY130 인버터 예제",
    "SKY130 inverter"
  ],
  [
    "SKY130 선택 시 1.8 V NMOS/PMOS 공정 모델을 사용합니다. 공개 PDK 결과는 제조 승인과 별개입니다.",
    "SKY130 uses 1.8 V NMOS/PMOS process models. Public PDK results are separate from manufacturing approval."
  ],
  [
    "모델",
    "Model"
  ],
  [
    "범용 예제",
    "Generic models"
  ],
  [
    "회로 이름",
    "Circuit name"
  ],
  [
    "온도 (°C)",
    "Temperature (°C)"
  ],
  [
    "+ 소자 추가",
    "+ Add device"
  ],
  [
    "연결도 · 같은 net 이름은 전기적으로 연결됩니다",
    "Connectivity · identical net names are electrically connected"
  ],
  [
    "해석",
    "Analysis"
  ],
  [
    "동작점 (OP)",
    "Operating point (OP)"
  ],
  [
    "AC 주파수 응답",
    "AC frequency response"
  ],
  [
    "과도해석 (Transient)",
    "Transient"
  ],
  [
    "ERC / 넷리스트 확인",
    "Check ERC / netlist"
  ],
  [
    "시뮬레이션 실행",
    "Run simulation"
  ],
  [
    "Post-layout · 추출 회로 재시뮬레이션",
    "Post-layout · simulate extracted circuit"
  ],
  [
    "검증 창에서 LVS와 PEX가 통과한 실행 ID를 입력하세요. 위 회로에는 전원·입력 소스와 RLC 부하를 구성하고, 아래에 추출 핀과 testbench net의 연결을 지정합니다.",
    "Enter a verification run ID with passing LVS and PEX. Configure sources and RLC loads above, then map every extracted pin to a testbench net below."
  ],
  [
    "검증 실행 ID",
    "Verification run ID"
  ],
  [
    "핀 연결 JSON",
    "Pin mapping JSON"
  ],
  [
    "PEX 회로 실행",
    "Simulate PEX circuit"
  ],
  [
    "실험 관리 · corners / 온도 / sweep / 합격 기준",
    "Experiments · corners / temperature / sweep / acceptance"
  ],
  [
    "최대 30개 조합. 측정은 전체 샘플을 사용합니다. mean은 샘플 산술 평균입니다.",
    "Up to 30 combinations. Measurements use all samples; mean is the arithmetic sample mean."
  ],
  [
    "Corners (쉼표 구분)",
    "Corners (comma-separated)"
  ],
  [
    "온도 °C (쉼표 구분)",
    "Temperature °C (comma-separated)"
  ],
  [
    "Sweep 소자 (선택)",
    "Sweep device (optional)"
  ],
  [
    "Sweep 값 (SI, 쉼표 구분)",
    "Sweep values (SI, comma-separated)"
  ],
  [
    "측정 신호",
    "Measured signal"
  ],
  [
    "통계",
    "Statistic"
  ],
  [
    "하한",
    "Lower bound"
  ],
  [
    "상한",
    "Upper bound"
  ],
  [
    "실험 실행",
    "Run experiment"
  ],
  [
    "실험 결과 JSON",
    "Export experiment JSON"
  ],
  [
    "실행 이력",
    "Run history"
  ],
  [
    "측정값",
    "Measurement"
  ],
  [
    "판정",
    "Result"
  ],
  [
    "파형",
    "Waveform"
  ],
  [
    "보기",
    "View"
  ],
  [
    "실행 전입니다. 회로 입력은 이 브라우저에 저장됩니다.",
    "Not run yet. Circuit inputs are saved in this browser."
  ],
  [
    "검사 · 해석 결과",
    "Check and analysis results"
  ],
  [
    "신호",
    "Signal"
  ],
  [
    "표시",
    "Display"
  ],
  [
    "실수값",
    "Real"
  ],
  [
    "크기",
    "Magnitude"
  ],
  [
    "위상 (°)",
    "Phase (°)"
  ],
  [
    "결과 JSON 저장",
    "Export result JSON"
  ],
  [
    "마지막 값",
    "Last value"
  ],
  [
    "단위",
    "Unit"
  ],
  [
    "SPICE 넷리스트",
    "SPICE netlist"
  ],
  [
    "실행 로그",
    "Execution log"
  ],
  [
    "이름",
    "Name"
  ],
  [
    "소자",
    "Device"
  ],
  [
    "폭 W (m)",
    "Width W (m)"
  ],
  [
    "길이 L (m)",
    "Length L (m)"
  ],
  [
    "저항 (Ω)",
    "Resistance (Ω)"
  ],
  [
    "용량 (F)",
    "Capacitance (F)"
  ],
  [
    "인덕턴스 (H)",
    "Inductance (H)"
  ],
  [
    "전압 (V)",
    "Voltage (V)"
  ],
  [
    "전류 (A)",
    "Current (A)"
  ],
  [
    "AC 크기",
    "AC amplitude"
  ],
  [
    "삭제",
    "Remove"
  ],
  [
    "Sweep 소자",
    "Sweep device"
  ],
  [
    "시작",
    "Start"
  ],
  [
    "종료",
    "Stop"
  ],
  [
    "간격",
    "Step"
  ],
  [
    "점 / decade",
    "Points / decade"
  ],
  [
    "구조적 ERC 통과 (공정 sign-off ERC 아님)",
    "Structural ERC passed (not process sign-off ERC)"
  ],
  [
    "Post-layout: 추출된 회로 연결 사용, 구조적 ERC 별도 미실행",
    "Post-layout: using extracted connectivity; structural ERC was not run separately"
  ],
  [
    "추출 회로를 ngspice로 해석 중…",
    "Simulating extracted circuit with ngspice…"
  ],
  [
    "실험 실행 중… 각 조합의 원본 데이터와 판정을 저장합니다.",
    "Running experiment… Saving raw data and acceptance results for each combination."
  ],
  [
    "실행 실패",
    "Run failed"
  ],
  [
    "소자는 최대 128개입니다.",
    "Up to 128 devices are supported."
  ],
  [
    "설계 DB의 회로를 불러왔습니다.",
    "Circuit loaded from the design DB."
  ],
  [
    "JSON 최대 크기는 256 KiB입니다.",
    "Circuit JSON is limited to 256 KiB."
  ],
  [
    "회로를 불러왔습니다.",
    "Circuit loaded."
  ],
  [
    "ngspice 실행 중…",
    "Running ngspice…"
  ],
  [
    "요청 실패",
    "Request failed"
  ],
  [
    "브라우저 저장 실패: JSON으로 내보내세요.",
    "Browser storage failed. Export JSON to keep your inputs."
  ],
  [
    "PDK · 규칙 · 검증",
    "PDK · Rules · Verification"
  ],
  [
    "검증 패널 닫기",
    "Close verification panel"
  ],
  [
    "PDK 기본값을 선택하고 설계 파일을 불러오세요. 프로젝트 제약을 추가하면 기본 DRC/LVS와 함께 검사합니다.",
    "Choose a PDK profile and upload your design files. Project constraints are checked alongside the default DRC/LVS rules."
  ],
  [
    "설정 JSON 가져오기",
    "Import settings JSON"
  ],
  [
    "설정 JSON 저장",
    "Export settings JSON"
  ],
  [
    "기본값으로 초기화",
    "Reset to defaults"
  ],
  [
    "설정은 이 브라우저에 저장됩니다. GDS와 SPICE 파일 내용은 저장하지 않습니다.",
    "Settings are saved in this browser. GDS and SPICE file contents are not stored."
  ],
  [
    "1. PDK와 검사 범위",
    "1. PDK and check scope"
  ],
  [
    "SKY130 · 공개 PDK",
    "SKY130 · Public PDK"
  ],
  [
    "검토 범위",
    "Review scope"
  ],
  [
    "셀 — DRC / LVS",
    "Cell — DRC / LVS"
  ],
  [
    "칩 — DRC / LVS / 밀도 / ERC / antenna",
    "Chip — DRC / LVS / density / ERC / antenna"
  ],
  [
    "설치된 rule deck 확인 중…",
    "Checking installed rule decks…"
  ],
  [
    "현재 PDK는 SKY130입니다. Magic 옵션을 켜면 RC 추출과 antenna를 검사합니다. 공정 ERC와 제조기관의 최종 승인은 별도로 필요합니다.",
    "The current PDK is SKY130. Enable Magic for RC extraction and antenna checks. Process ERC and final manufacturing approval remain separate requirements."
  ],
  [
    "2. 설계 파일",
    "2. Design files"
  ],
  [
    "GDS 파일 · 최대 20 MiB",
    "GDS file · up to 20 MiB"
  ],
  [
    "회로 SPICE · 최대 2 MiB",
    "Circuit SPICE · up to 2 MiB"
  ],
  [
    "최상위 셀",
    "Top cell"
  ],
  [
    "GDS를 불러오면 자동으로 제안합니다",
    "Suggested automatically after loading GDS"
  ],
  [
    "LVS 기판 net",
    "LVS substrate net"
  ],
  [
    "SPICE 소자 치수 단위",
    "SPICE device dimension units"
  ],
  [
    "SKY130 µm (예: W=0.65)",
    "SKY130 µm (e.g. W=0.65)"
  ],
  [
    "SI (예: W=0.65u)",
    "SI (e.g. W=0.65u)"
  ],
  [
    "Magic PEX·antenna 검사 포함 (WSL)",
    "Include Magic PEX / antenna checks (WSL)"
  ],
  [
    "GDS의 셀 이름·레이어·단위를 자동으로 읽습니다.",
    "Cell names, layers and units are read automatically from GDS."
  ],
  [
    "SPICE를 선택하면 VNB / VSS 등 기판 net 후보를 제안합니다. 외부 .include / .lib 없이 회로 정의를 포함해야 합니다. mockTech 도형은 SKY130으로 자동 변환하지 않습니다.",
    "SPICE pins suggest substrate nets such as VNB / VSS. Include the circuit definition without external .include / .lib files. mockTech geometry is not automatically converted to SKY130."
  ],
  [
    "3. 프로젝트 제약 · 선택",
    "3. Project constraints · optional"
  ],
  [
    "PDK 규칙에 추가할 최소 폭·간격·면적을 입력하세요. PDK 원본 규칙은 그대로 검사합니다.",
    "Add minimum width, spacing and area constraints. The original PDK rules are still checked."
  ],
  [
    "최대 셀 가로 (µm)",
    "Maximum cell width (µm)"
  ],
  [
    "최대 셀 세로 (µm)",
    "Maximum cell height (µm)"
  ],
  [
    "제한 없음",
    "No limit"
  ],
  [
    "+ 레이어 규칙 추가",
    "+ Add layer rule"
  ],
  [
    "폭·간격은 µm, 면적은 µm² 단위입니다. GDS에서 읽은 레이어를 선택할 수 있으며, 적용할 도형이 없는 규칙은 미실행으로 표시합니다.",
    "Width and spacing use µm; area uses µm². Select layers read from GDS. Rules without applicable geometry are marked not run."
  ],
  [
    "검사 실행",
    "Run checks"
  ],
  [
    "아직 검사를 실행하지 않았습니다.",
    "Checks have not been run yet."
  ],
  [
    "검사 결과",
    "Verification results"
  ],
  [
    "JSON 보고서 저장",
    "Export JSON report"
  ],
  [
    "검토 자료 ZIP",
    "Review evidence ZIP"
  ],
  [
    "PEX SPICE 저장",
    "Export PEX SPICE"
  ],
  [
    "검사",
    "Check"
  ],
  [
    "상태",
    "Status"
  ],
  [
    "상세",
    "Details"
  ],
  [
    "Sign-off: 미인증",
    "Sign-off: not qualified"
  ],
  [
    "검토 준비 상태는 선택한 범위와 프로젝트 제약에 대한 결과입니다. 제조용 sign-off에는 해당 공정과 프로젝트의 추가 요구사항 확인이 필요합니다.",
    "Review readiness covers the selected scope and project constraints. Manufacturing sign-off requires additional process and project checks."
  ],
  [
    "위반 위치 · LVS 비교 · 실행 정보",
    "Violation locations · LVS comparison · Run information"
  ],
  [
    "레이어",
    "Layer"
  ],
  [
    "규칙",
    "Rule"
  ],
  [
    "최소 폭",
    "Minimum width"
  ],
  [
    "최소 간격",
    "Minimum spacing"
  ],
  [
    "최소 면적",
    "Minimum area"
  ],
  [
    "최소값 (µm)",
    "Minimum (µm)"
  ],
  [
    "최소 면적 (µm²)",
    "Minimum area (µm²)"
  ],
  [
    "통과",
    "Passed"
  ],
  [
    "위반 / 불일치",
    "Violation / mismatch"
  ],
  [
    "실행 오류",
    "Execution error"
  ],
  [
    "미실행",
    "Not run"
  ],
  [
    "브라우저 저장을 사용할 수 없습니다. JSON 저장을 이용하세요.",
    "Browser storage is unavailable. Export settings as JSON."
  ],
  [
    "레이어 규칙은 최대 64개입니다.",
    "Up to 64 layer rules are supported."
  ],
  [
    "GDS 파일을 읽을 수 없습니다.",
    "Cannot read the GDS file."
  ],
  [
    "GDS 셀과 레이어를 읽는 중…",
    "Reading GDS cells and layers…"
  ],
  [
    "GDS 크기는 최대 20 MiB입니다.",
    "GDS files are limited to 20 MiB."
  ],
  [
    "SPICE 크기는 최대 2 MiB입니다.",
    "SPICE files are limited to 2 MiB."
  ],
  [
    "설정을 JSON으로 저장했습니다. 파일 내용은 포함하지 않습니다.",
    "Settings exported as JSON. Design file contents are not included."
  ],
  [
    "설정 JSON은 최대 128 KiB입니다.",
    "Settings JSON is limited to 128 KiB."
  ],
  [
    "프로젝트 설정을 적용했습니다.",
    "Project settings applied."
  ],
  [
    "PDK 기본값으로 초기화했습니다.",
    "Reset to PDK defaults."
  ],
  [
    "검사 중입니다. 검사별 최대 실행 시간은 5분입니다.",
    "Running checks. Each check has a 5-minute timeout."
  ],
  [
    "GDS를 선택해 셀·레이어 읽기를 완료하세요.",
    "Select a GDS file and wait for cell/layer inspection to complete."
  ],
  [
    "검토 준비 완료 · 제조 sign-off 미인증",
    "Ready for review · manufacturing sign-off not qualified"
  ],
  [
    "선택한 범위의 검사가 통과했습니다.",
    "Checks for the selected scope passed."
  ],
  [
    "체크리스트를 확인하세요. 미실행·오류는 통과로 처리하지 않습니다.",
    "Review the checklist. Missing or failed runs are not counted as passing."
  ],
  [
    "검토 자료를 만들지 못했습니다.",
    "Could not create the review evidence bundle."
  ],
  [
    "PEX 검사를 포함하여 실행하세요.",
    "Run verification with PEX enabled."
  ],
  [
    "이 브라우저의 이전 프로젝트 설정을 복원했습니다.",
    "Previous project settings restored from this browser."
  ],
  [
    "저장된 설정이 유효하지 않아 기본값을 적용했습니다.",
    "Saved settings are invalid; defaults have been applied."
  ],
  [
    "에이전트",
    "Agents"
  ],
  [
    "레이어 목록",
    "Layers"
  ],
  [
    "SKILL 실행 기록",
    "SKILL transcript"
  ],
  [
    "생성",
    "Build"
  ],
  [
    "셀",
    "cell"
  ],
  [
    "도형",
    "shapes"
  ],
  [
    "인스턴스",
    "instances"
  ],
  [
    "명령",
    "ops"
  ],
  [
    "끌어서 이동 · 휠로 확대/축소",
    "drag to pan · wheel to zoom"
  ],
  [
    "에이전트 → virtuoso-bridge → 하나의 설계 데이터베이스",
    "agents → virtuoso-bridge → one mock Virtuoso design database"
  ],
  [
    "아래 기록은 실제 전달된 SKILL 명령입니다",
    "every line below crossed the wire as SKILL"
  ],
  [
    "무엇을 만들까요?  e.g. STDLIB에 NAND2 셀 만들고 ROW에 4개 배치해줘",
    "What would you like to build? e.g. Create NAND2 in STDLIB and place four instances in ROW"
  ],
  [
    "준비되었습니다. 아직 생성된 설계가 없습니다.",
    "Ready. Nothing has been built yet."
  ],
  [
    "에이전트도 참여할 수 있습니다",
    "Agents can join too"
  ],
  [
    "설계 셀을 기다리는 중…",
    "waiting for a cellview…"
  ],
  [
    "서버 연결이 끊겼습니다 — 재시도 중",
    "lost contact with the floor — retrying"
  ],
  [
    "캔버스 아래 입력란에 만들고 싶은 설계를 입력하세요. 전달된 SKILL 명령과 응답이 이곳에 표시됩니다.",
    "Type what you want in the box under the canvas — 만들고 싶은 것을 캔버스 아래 입력란에 적으세요. Every SKILL call it sends appears here, with the reply."
  ],
  [
    "회로 연결도",
    "Circuit connectivity"
  ],
  [
    "시뮬레이션 파형",
    "Simulation waveform"
  ],
  [
    "에이전트 패널 너비 조절",
    "resize the agents panel"
  ],
  [
    "실행 기록 패널 너비 조절",
    "resize the transcript panel"
  ]
];
  pairs.push(['여러 신호 함께','Multiple signals'],['표시할 신호','Signals to display'],['확대 +','Zoom in +'],['축소 −','Zoom out −'],['전체 보기','Fit all'],['시간축 이동','Pan axis'],['측정 커서','Measurement cursor'],['신호별 마지막 값','Last value by signal']);
  pairs.push(['레이아웃 셀','Layout cell']);
  pairs.push(
    ['선택 셀 검증','Verify selected cell'], ['현재 셀 검사','Check current cell'],
    ['레이어 매핑','Layer mapping'], ['mockTech · 교육용 형상 검사','mockTech · Educational geometry checks'],
    ['SKY130 · 명시적 PDK 레이어 매핑 + 실제 DRC/LVS','SKY130 · Explicit PDK layer mapping + real DRC/LVS'],
    ['DB와 하위 셀을 읽어 입력을 고정하고, GDS 내보내기 전후 형상을 비교합니다. 화면 렌더링 자체는 별도 확인이 필요합니다.','Snapshot the DB and its hierarchy, then compare geometry before and after GDS export. Canvas rendering requires a separate check.'],
    ['SKY130 매핑은 현재 형상이 SKY130 공정 구조를 갖춘 경우에 선택하세요. mock via는 물리 via 구조로 자동 변환하지 않습니다.','Select SKY130 mapping for layouts built with SKY130 process structures. Mock vias are not converted into physical via structures.'],
    ['기준 SPICE','Reference SPICE'], ['SPICE 치수 단위','SPICE dimension units'],
    ['Magic PEX·antenna 포함 (엔진과 PDK 설치 필요)','Include Magic PEX and antenna checks (engine and PDK required)'],
    ['입력 또는 셀이 변경되었습니다. 재검사가 필요합니다.','The input or cell changed. Run verification again.'],
    ['검사한 GDS 저장','Download checked GDS'], ['보고서 JSON 저장','Download report JSON'],
    ['외부 검증 자료 ZIP','External verification evidence ZIP'], ['형상 · 연결 · 검증 상세','Geometry, connectivity and verification details'],
    ['DB 읽기 · GDS 비교 · 선택한 검사를 실행 중입니다…','Reading DB, comparing GDS and running selected checks…'],
    ['검사가 완료되었습니다. 각 검사 상태를 확인하세요.','Checks complete. Review each check status.']
  );
  pairs.push(
    ['DRC / LVS · 물리 검증','DRC / LVS · Physical verification'],
    ['DRC · 설계 규칙','DRC · Design rules'],
    ['LVS · 회로 일치','LVS · Circuit equivalence'],
    ['GDS 형상을 PDK rule deck으로 검사합니다. FEOL·BEOL·off-grid·floating metal 검사를 활성화합니다.','Check GDS geometry against the PDK rule deck with FEOL, BEOL, off-grid and floating-metal checks enabled.'],
    ['확인 → 위반 위치 수정 → GDS 재검사','Inspect → fix violation locations → recheck GDS'],
    ['GDS에서 추출한 소자·연결을 기준 SPICE와 비교합니다. 셀 이름·핀·기판 net·소자 치수 단위를 확인하세요.','Compare devices and connections extracted from GDS against reference SPICE. Check cell names, pins, substrate net and device dimension units.'],
    ['GDS + 기준 SPICE → 추출 회로 비교','GDS + reference SPICE → compare extracted circuits'],
    ['Drawing의 선택 셀이 자동으로 검사되지는 않습니다. 아래에 업로드한 GDS와 SPICE가 검사 대상입니다.','Verification uses the GDS and SPICE uploaded below. Selecting a cell in Drawing does not select its verification inputs.'],
    ['실행 전 확인','Before running'],
    ['Deck 설치 여부는 엔진 실행 성공을 보장하지 않습니다. 실제 실행 결과를 확인하세요.','An installed deck does not guarantee a successful engine run. Check the actual results.'],
    ['DRC / LVS 검사 실행','Run DRC / LVS'],
    ['DRC / LVS 핵심 결과','DRC / LVS summary'],
    ['입력이 변경되었습니다. 아래 결과는 이전 실행 기록입니다. 현재 입력으로 다시 검사하세요.','Inputs changed. The results below belong to an earlier run. Rerun verification with the current inputs.'],
    ['DRC 위반 위치','DRC violation locations'],
    ['규칙·셀·좌표 검색','Search rules, cells or coordinates'],
    ['예: met1, sky130, 10.05','Example: met1, sky130, 10.05'],
    ['규칙','Rule'],['셀','Cell'],['위치 / 형상 (µm)','Location / geometry (µm)'],
    ['LVS 회로 비교','LVS circuit comparison'],
    ['불일치 시 핀·전원·기판 연결, 소자 모델과 W/L을 확인하세요. 상세 net·소자 비교는 ZIP의 lvs.lvsdb를 KLayout에서 여세요.','For mismatches, check pins, supply and substrate connections, device models and W/L. Open lvs.lvsdb from the ZIP in KLayout for detailed net and device comparisons.'],
    ['레이아웃 회로','Layout circuit'],['기준 회로','Reference circuit'],['비교 상태','Comparison status'],
    ['실행 조건 · 입력 및 rule deck SHA-256','Run settings · input and rule deck SHA-256'],
    ['보고서는 실행 시점의 입력에만 적용됩니다. ZIP에는 입력 사본·deck·로그·원본 결과 DB가 포함됩니다.','Reports apply only to the inputs at run time. The ZIP includes input snapshots, decks, logs and native result databases.'],
    ['GDS와 최상위 셀','GDS and top cell'],['GDS를 선택하고 최상위 셀을 확인하세요.','Select GDS and confirm the top cell.'],
    ['DRC deck 설치가 필요합니다.','Install the DRC deck.'],['LVS deck 설치가 필요합니다.','Install the LVS deck.'],
    ['LVS 기준 SPICE','LVS reference SPICE'],
    ['SPICE 없음: DRC만 실행되며 LVS는 미실행, 검토는 보류됩니다.','No SPICE: DRC runs, LVS is not run, and review remains blocked.'],
    ['준비됨','Ready'],['전체 위반','Total violations'],['보고서 위치','Reported locations'],['검색 결과','Search matches'],['표시','Displayed'],['추출 소자','Extracted devices'],
    ['일부 위치만 표시합니다. 전체 결과는 ZIP의 drc.lyrdb에서 확인하세요.','Only some locations are displayed. See drc.lyrdb in the ZIP for the full results.'],
    ['DRC 위반이 없습니다.','No DRC violations.'],
    ['표시할 위치가 없습니다. 검사 상태와 실행 로그를 확인하세요.','No locations to display. Check the status and engine log.'],
    ['업로드한 GDS가 실행한 DRC deck을 통과했습니다.','The uploaded GDS passed the executed DRC deck.'],
    ['아래 규칙과 위치를 확인하고 레이아웃을 수정한 뒤 GDS를 다시 업로드하세요.','Review the rules and locations below, fix the layout and upload the revised GDS.'],
    ['ZIP의 drc.log에서 deck·입력·엔진 실행 오류를 확인하세요.','Check drc.log in the ZIP for deck, input or engine errors.'],
    ['DRC 입력과 deck을 준비한 뒤 다시 실행하세요.','Prepare DRC inputs and deck, then rerun.'],
    ['추출 소자가 있고 모든 회로 비교가 일치합니다.','Devices were extracted and all circuit comparisons match.'],
    ['핀·전원·기판 net과 소자 모델·W/L을 확인하고 다시 비교하세요.','Check pins, supply and substrate nets, device models and W/L, then compare again.'],
    ['ZIP의 lvs.log에서 SPICE 구문·모델·엔진 실행 오류를 확인하세요.','Check lvs.log in the ZIP for SPICE syntax, model or engine errors.'],
    ['기준 SPICE를 추가해야 LVS를 실행할 수 있습니다.','Add reference SPICE to run LVS.'],
    ['비교된 회로가 없습니다. LVS 상태를 확인하세요.','No circuits were compared. Check the LVS status.']
  );
  const lookup=new Map();
  pairs.push(
    ['설계 검증 대시보드','Design verification dashboard'],
    ['회로 검증과 업로드한 레이아웃 검증은 각각의 입력에 대한 결과입니다. PEX 비교는 같은 검증 실행의 기준 SPICE와 추출 회로를 연결합니다.','Circuit and uploaded-layout checks apply to their own inputs. PEX comparison links the reference SPICE and extracted circuit from the same verification run.'],
    ['대상 / 근거','Target / evidence'],
    ['공정 ERC·STA·DFF setup/hold·Monte Carlo·IR/EM·공인 sign-off는 이 검증에 포함되지 않습니다.','Process ERC, STA, DFF setup/hold, Monte Carlo, IR/EM and foundry sign-off are outside this review.'],
    ['기능 · PVT · 지연 / 전력 · PEX 비교','Function · PVT · timing / power · PEX comparison'],
    ['현재 회로의 입력 소스를 모든 논리 조합으로 구동합니다. 전압마다 입력 high도 함께 변경합니다. 한 번에 최대 30개 PVT 조합, PEX 비교는 최대 15개 조합입니다.','Drive the current circuit through all logic combinations, scaling input high with supply voltage. Up to 30 PVT combinations, or 15 for paired PEX comparison.'],
    ['기대 논리','Expected logic'],['입력 소스 순서','Input source order'],['전원 소스','Supply source'],['출력 net','Output net'],
    ['입력 순서는 A,B,C입니다. MUX2는 A,B,S이며 S=1일 때 B를 선택합니다.','Input order is A,B,C. For MUX2 use A,B,S; S=1 selects B.'],
    ['PVT 온도 (°C)','PVT temperature (°C)'],['PVT 전압 (V)','PVT voltage (V)'],['TT / FF / SS 프리셋','TT / FF / SS preset'],
    ['입력 조합 유지 (ns)','Vector hold time (ns)'],['입력 edge (ns)','Input edge (ns)'],
    ['최대 지연 (ns)','Maximum delay (ns)'],['최대 전이 (ns)','Maximum transition (ns)'],['최대 평균 전력 (µW)','Maximum average power (µW)'],
    ['기본 허용값은 학습용입니다. 프로젝트 사양으로 바꾸세요. 논리는 조합 중앙에서 20%/80% 기준으로 판정합니다. 지연은 관측한 단일 입력 전이의 50% 교차, 출력 전이는 10–90%입니다. 평균 전력은 원본 샘플의 시간 적분값입니다.','Default limits are educational; enter your project specifications. Logic is sampled at vector midpoints using 20%/80% thresholds. Delay uses 50% crossings of observed single-input transitions; output transition is 10–90%. Power is integrated over the full raw waveform.'],
    ['기능 / PVT 검증 실행','Run function / PVT review'],['검증 JSON 저장','Export review JSON'],
    ['동일 조건으로 PEX 전후 비교','Compare pre/post PEX under identical conditions'],
    ['LVS·PEX가 통과한 실행 ID와 모든 핀 연결을 지정하세요. 편집기의 전원·입력·RLC 부하만 사용하며, 소자 회로는 해당 실행의 기준 SPICE와 PEX에서 가져옵니다.','Provide a run with passing LVS/PEX and map every port. Only sources and RLC loads come from the editor; devices come from that run’s reference SPICE and PEX.'],
    ['PEX 비교 실행 ID','PEX comparison run ID'],['PEX 핀 연결 JSON','PEX port mapping JSON'],['PEX 전후 비교 실행','Run pre/post PEX comparison'],
    ['현재 비교는 flat SKY130 1.8 V X/R/C 회로를 지원합니다. 측정한 전이만 평가하며 전체 timing arc·Liberty 특성화를 대신하지 않습니다.','Comparison supports flat SKY130 1.8 V X/R/C circuits. Only observed transitions are evaluated; this is not full timing-arc or Liberty characterization.'],
    ['검증 전입니다.','Review has not run.'],
    ['입력 또는 조건이 변경되었습니다. 이전 결과이므로 재검사하세요.','Inputs or conditions changed. These results are stale; rerun review.'],
    ['기능','Function'],['평균 전력 (µW)','Average power (µW)'],['판정','Verdict'],['파형 / 진리표','Waveform / truth table'],
    ['입력 조합','Input vector'],['기대 출력','Expected output'],['실제 출력 (V)','Measured output (V)'],
    ['PEX 비교표의 값은 기준 → 추출 (차이)입니다.','PEX comparison values are reference → extracted (difference).'],
    ['지연 (ns)','Delay (ns)'],['전이 (ns)','Transition (ns)'],['전력 (µW)','Power (µW)'],
    ['실패','Failed'],['미지원','Unsupported'],['재검사 필요','Rerun required'],
    ['논리 기능 / PVT','Logic function / PVT'],['관측 전이 지연 / PVT','Observed transition delay / PVT'],['평균 전력 / PVT','Average power / PVT'],
    ['회로 검증 실행 필요','Run circuit review'],['레이아웃 검증 실행 필요','Run layout verification'],
    ['PEX 전후 비교','Pre/post PEX comparison'],['동일 검증 실행의 LVS / PEX 필요','LVS / PEX from the same verification run required'],
    ['공정 ERC / STA / IR·EM / DFF / Monte Carlo','Process ERC / STA / IR·EM / DFF / Monte Carlo'],
    ['별도 도구·모델·검증 흐름 필요','Additional tools, models and verification flow required'],
    ['기준','Reference'],['추출','Extracted'],
    ['검증 실행 중… 전체 파형으로 기능·지연·전력을 측정합니다.','Review running… measuring function, delay and power using full waveforms.']
  );
  const normalize=value=>value.trim().replace(/\s+/g,' ');
  for(const pair of pairs)for(const value of pair)lookup.set(normalize(value),pair);
  let lang='ko';try{lang=localStorage.getItem('mv.lang')==='en'?'en':'ko';}catch{}
  const originals=new WeakMap(), attributes=new WeakMap();
  const roots='body>header,#circuit-panel,#verification-panel,#layout-check-panel,main h2,.layout-controls,.ask,.grip,.status,.empty,#lost,#tabs .tab:not([data-key])';
  const excluded='script,style,pre,code,svg,input,textarea,[data-no-translate],#circuit-values,#circuit-netlist,#circuit-log,#verify-detail,.ev,.mv-about-back';
  const formats=[
    [/^(통과|실패|실행 오류|미실행) · ((?:review|comparison)-[a-f0-9]+)$/,m=>`${({통과:'Passed',실패:'Failed','실행 오류':'Execution error',미실행:'Not run'})[m[1]]} · ${m[2]}`],
    [/^해석 완료 · (.+)s$/,m=>`Simulation complete · ${m[1]}s`],
    [/^실험 (\w+) · (\d+)개 조합$/,m=>`Experiment ${m[1]} · ${m[2]} combinations`],
    [/^(CIRCUITS\/.*\/schematic)에 저장했습니다\.$/,m=>`Saved to ${m[1]}.`],
    [/^최상위 셀 (\d+)개 · 레이어 (\d+)개 · DBU (.+) µm$/,m=>`${m[1]} top cells · ${m[2]} layers · DBU ${m[3]} µm`],
    [/^SPICE 핀에서 기판 net (.+)을 제안했습니다\. 확인 후 실행하세요\.$/,m=>`Suggested substrate net ${m[1]} from SPICE pins. Confirm before running.`],
    [/^설정을 불러오지 못했습니다: (.+)$/,m=>`Could not load settings: ${m[1]}`],
    [/^검토 보류: (.+)$/,m=>`Review blocked: ${m[1]}`],
    [/^(\d+)개 회로 비교$/,m=>`${m[1]} circuits compared`],
    [/^(\d+)개 위반$/,m=>`${m[1]} violations`],
    [/^(\d+)개 피드백$/,m=>`${m[1]} feedback markers`],
    [/^(.+) · (\d+) samples \((\d+) 표시\) · X: (.+)$/,m=>`${m[1]} · ${m[2]} samples (${m[3]} displayed) · X: ${m[4].replace('동작점','operating point')}`],
    [/^(.+) PULSE: (.+) \(JSON에서 편집\)$/,m=>`${m[1]} PULSE: ${m[2]} (edit in JSON)`],
    [/^(DRC|LVS|DENSITY): .+$/,m=>m[0].replaceAll('준비됨','ready').replaceAll('deck 설치 필요','install deck')]
  ];
  function translate(value){
    const key=normalize(value), pair=lookup.get(key);
    if(pair)return pair[lang==='en'?1:0];
    if(lang==='en')for(const [pattern,format] of formats){const match=key.match(pattern);if(match)return format(match);}
    return value;
  }
  function text(node){
    const parent=node.parentElement;if(!parent||parent.closest(excluded))return;
    const previous=originals.get(node), source=previous&&node.data===previous.output?previous.source:node.data;
    const translated=translate(source);
    if(translated!==source||previous){
      const output=translated===source?source:source.replace(source.trim(),translated);
      originals.set(node,{source,output});if(node.data!==output)node.data=output;
    }
  }
  let observer;
  function refresh(){
    observer?.disconnect();
    document.documentElement.lang=lang;
    for(const root of document.querySelectorAll(roots)){
      const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);let node;
      while((node=walker.nextNode()))text(node);
      for(const element of [root,...root.querySelectorAll('[placeholder],[aria-label],[title]')]){
        if(element.closest('[data-no-translate],.ev,.mv-about-back'))continue;
        let saved=attributes.get(element);if(!saved){saved={};attributes.set(element,saved);}
        for(const attr of ['placeholder','aria-label','title'])if(element.hasAttribute(attr)){
          const current=element.getAttribute(attr), prev=saved[attr];
          const source=prev&&current===prev.output?prev.source:current, output=translate(source);
          saved[attr]={source,output};if(current!==output)element.setAttribute(attr,output);
        }
      }
    }
    document.querySelectorAll('[data-ui-language]').forEach(el=>el.value=lang);
    observer?.observe(document.body,{subtree:true,childList:true,characterData:true});
  }
  function setLanguage(value){
    lang=value==='en'?'en':'ko';try{localStorage.setItem('mv.lang',lang);}catch{}
    refresh();window.dispatchEvent(new Event('floor-language-change'));
  }
  window.floorI18n={get lang(){return lang;},setLanguage,refresh,t:translate};
  function mount(){
    for(const heading of document.querySelectorAll('body>header,.verify-heading,.circuit-heading')){
      const label=document.createElement('label');label.className='theme-control language-control';
      label.append(document.createTextNode('언어'));
      const select=document.createElement('select');select.dataset.uiLanguage='';select.setAttribute('aria-label','언어');
      for(const [value,name] of [['ko','한국어'],['en','English']]){const option=document.createElement('option');option.value=value;option.textContent=name;select.append(option);}
      select.value=lang;select.onchange=()=>setLanguage(select.value);label.append(select);
      heading.insertBefore(label,heading.querySelector('.theme-control'));
    }
    let scheduled=false;
    observer=new MutationObserver(records=>{
      if(scheduled||!records.some(r=>{const el=r.target.nodeType===1?r.target:r.target.parentElement;return el?.closest(roots)&&!el.closest(excluded);}))return;
      scheduled=true;queueMicrotask(()=>{scheduled=false;refresh();});
    });
    refresh();
  }
  window.addEventListener('storage',event=>{if(event.key==='mv.lang')setLanguage(event.newValue);});
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount,{once:true});else mount();
})();

/* The introduction panel for the design floor.
 *
 * mountAbout() takes the host's name and renders the shared explanation plus
 * the paragraph about that screen; it kept the shape when a second front end
 * was retired, since the next one costs a table entry rather than a rewrite. Korean and English
 * live side by side in one table rather than in two files, so a change to one
 * language is visibly a change to the other — translations drift when they
 * are kept apart.
 */

const ABOUT_LANG_KEY = "mv.lang";

const ABOUT_TEXT = {
  open:      { ko: "소개",            en: "About" },
  close:     { ko: "닫기",            en: "Close" },

  leadHead:  { ko: "이게 무엇인가",    en: "What this is" },
  lead: {
    ko: "Cadence Virtuoso 자리에 서는 테스트 더블입니다. 진짜 데몬의 프로토콜을 그대로 말하기 때문에, " +
        "virtuoso-bridge는 상대가 Virtuoso가 아니라는 것을 알지 못합니다. 라이선스도, EDA 서버도, " +
        "Virtuoso 프로세스도 없이 동작합니다.",
    en: "A test double standing where Cadence Virtuoso would. It speaks the real daemon's wire " +
        "protocol, so virtuoso-bridge cannot tell it is not talking to Virtuoso. No licence, no EDA " +
        "server, no Virtuoso process.",
  },

  flowHead:  { ko: "동작 방식",        en: "How it works" },
  flowNote: {
    ko: "브리지의 CLI와 Python API를 고친 데 없이 그대로 씁니다. 다른 것은 어디로 전화를 거느냐뿐입니다.",
    en: "The bridge's own CLI and Python API, unmodified. The only difference is where they dial.",
  },

  screenHead:{ ko: "이 화면",          en: "This screen" },

  limitsHead:{ ko: "하지 않는 것",     en: "What it does not do" },
  limits: {
    ko: [
      "레이아웃과 회로 그래프를 다룹니다. Cadence 회로도 편집·Maestro 전체 API는 구현돼 있지 않습니다.",
      "SKILL의 부분집합입니다. 없는 함수는 nil을 돌려주지 않고 소리 내어 실패합니다.",
      "KLayout SKY130 검증과 ngspice 회로 해석을 연결합니다. 구조적 ERC와 범용 모델은 공정 sign-off를 대신하지 않습니다.",
      "기술 파일은 작고 고정돼 있습니다 — 레이어 7종, via 정의 4종.",
    ],
    en: [
      "Layout and circuit graphs. Full Cadence schematic editing and Maestro APIs are not implemented.",
      "A subset of SKILL. A function it lacks fails loudly instead of returning nil.",
      "KLayout SKY130 verification and ngspice simulation are integrated. Structural ERC and generic models do not provide foundry sign-off.",
      "The technology is small and fixed — seven layers, four via definitions.",
    ],
  },

  whyHead:   { ko: "왜 소리 내어 실패하는가", en: "Why it fails loudly" },
  why: {
    ko: "조용히 틀린 성공이 이 프로젝트가 없애려는 유일한 실패입니다. 실제로 잡은 것들: " +
        "셀뷰를 닫으면 그린 도형이 사라지던 문제, 존재하지 않는 via 정의로도 via가 만들어지던 문제, " +
        "실행된 적 없는 셸 명령이 성공으로 보고되던 문제.",
    en: "A quietly wrong success is the one failure this project exists to eliminate. Caught so far: " +
        "closing a cellview emptied the cell, a via could be drawn from a definition the technology " +
        "did not have, and a shell command that never ran was reported as having succeeded.",
  },

  repo:      { ko: "저장소",          en: "Repository" },
};

const ABOUT_SCREEN = {
  floor: {
    ko: "에이전트 설계 현장이자, 이 프로젝트의 유일한 화면입니다. 아래 입력란에 원하는 것을 " +
        "말로 적으면 계획으로 바뀌고, 검증을 통과한 것만 실제로 그려집니다. 에이전트들도 같은 " +
        "디자인 DB에서 일하며, 각자 자기 레인 — 데몬 포트 앞에 선 기록용 프록시 — 을 통해 " +
        "붙습니다. 기록은 mock 안이 아니라 전선 위에서 이뤄지므로, 여기 보이는 모든 줄은 진짜 " +
        "Virtuoso가 받았을 바로 그 SKILL입니다. 사람이 적은 요청도 예외가 아니라 자기 레인으로 " +
        "남습니다.",
    en: "The agent design floor, and this project's only screen. Say what you want in the box " +
        "below and it becomes a plan; only what passes validation is ever drawn. Agents work in " +
        "the same design database, each through its own lane — a recording proxy standing where " +
        "the daemon's port would be. Recording happens on the wire rather than inside the mock, " +
        "so every line here is exactly the SKILL a real Virtuoso would have received, a typed " +
        "request included.",
  },
};

const ABOUT_FLOW = {
  floor: "agent, or your request  →  plan  →  validate  →  virtuoso-bridge\n" +
         "  →  lane (recording proxy)  →  mock-virtuoso  →  design database  →  read back",
};

const ABOUT_CSS = `
.mv-about-btn{background:none;border:1px solid var(--border,#30363d);color:var(--dim,#8b949e);border-radius:999px;
  padding:2px 11px;font:inherit;font-size:11px;cursor:pointer}
.mv-about-btn:hover{color:var(--ink,#e6edf3);border-color:var(--hi,#4493f8)}
.mv-about-back{position:fixed;inset:0;background:rgba(2,5,10,.72);display:flex;
  align-items:center;justify-content:center;z-index:9999;padding:24px}
.mv-about-back[hidden]{display:none}
.mv-about{background:var(--panel,#0f151d);border:1px solid var(--edge,#263041);border-radius:10px;max-width:760px;
  width:100%;max-height:100%;overflow:auto;color:var(--ink,#c9d1d9);
  font:13px/1.65 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  box-shadow:0 18px 50px rgba(0,0,0,.55)}
.mv-about header{display:flex;align-items:center;gap:12px;padding:16px 20px;
  border-bottom:1px solid var(--edge,#1d2431);position:sticky;top:0;background:var(--panel,#0f151d)}
.mv-about header img{width:26px;height:26px}
.mv-about h2{margin:0;font-size:15px;letter-spacing:.2px;color:var(--ink,#e6edf3)}
.mv-about .grow{flex:1}
.mv-lang{display:flex;border:1px solid var(--border,#30363d);border-radius:999px;overflow:hidden}
.mv-lang button{background:none;border:0;color:var(--dim,#8b949e);padding:3px 11px;font:inherit;
  font-size:11px;cursor:pointer}
.mv-lang button[aria-pressed="true"]{background:#1f6feb;color:#fff}
.mv-about .x{background:none;border:0;color:var(--dim,#8b949e);font:inherit;font-size:16px;
  cursor:pointer;padding:0 4px;line-height:1}
.mv-about .x:hover{color:var(--ink,#e6edf3)}
.mv-about section{padding:16px 20px;border-bottom:1px solid var(--edge,#161d26)}
.mv-about section:last-child{border-bottom:0}
.mv-about h3{margin:0 0 7px;font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--dim,#6e7681);font-weight:600}
.mv-about p{margin:0}
.mv-about pre{margin:9px 0 0;padding:10px 12px;background:var(--input,#0a0f16);border:1px solid var(--edge,#1d2431);
  border-radius:6px;color:var(--hi,#4493f8);font-size:11.5px;white-space:pre-wrap;word-break:break-word}
.mv-about ul{margin:0;padding-left:18px}
.mv-about li{margin:3px 0}
.mv-about a{color:var(--hi,#4493f8)}
.mv-about .foot{display:flex;gap:8px;align-items:baseline;font-size:11.5px;color:var(--dim,#6e7681)}
`;

function aboutLang() {
  if(window.floorI18n)return window.floorI18n.lang;
  try {
    const saved = localStorage.getItem(ABOUT_LANG_KEY);
    if (saved === "ko" || saved === "en") return saved;
  } catch (e) { /* private window, blocked storage: fall through to the default */ }
  return (navigator.language || "").toLowerCase().startsWith("ko") ? "ko" : "en";
}

function mountAbout(app) {
  const t = (key, lang) => ABOUT_TEXT[key][lang];
  let lang = aboutLang();

  const style = document.createElement("style");
  style.textContent = ABOUT_CSS;
  document.head.appendChild(style);

  const back = document.createElement("div");
  back.className = "mv-about-back";
  back.hidden = true;
  back.innerHTML = `
    <div class="mv-about" role="dialog" aria-modal="true" aria-label="About mock-virtuoso">
      <header>
        <img src="/favicon.svg" alt="">
        <h2>mock-virtuoso</h2>
        <div class="grow"></div>
        <div class="mv-lang">
          <button data-lang="ko">한국어</button><button data-lang="en">English</button>
        </div>
        <button class="x">✕</button>
      </header>
      <section><h3 data-k="leadHead"></h3><p data-k="lead"></p></section>
      <section><h3 data-k="flowHead"></h3><pre class="flow"></pre><p data-k="flowNote"
        style="margin-top:9px"></p></section>
      <section><h3 data-k="screenHead"></h3><p class="screen"></p></section>
      <section><h3 data-k="limitsHead"></h3><ul class="limits"></ul></section>
      <section><h3 data-k="whyHead"></h3><p data-k="why"></p></section>
      <section class="foot">
        <span data-k="repo"></span>
        <a href="https://github.com/kos2001/mock-virtuoso"
           target="_blank" rel="noreferrer">github.com/kos2001/mock-virtuoso</a>
      </section>
    </div>`;
  document.body.appendChild(back);

  function render() {
    for (const el of back.querySelectorAll("[data-k]")) el.textContent = t(el.dataset.k, lang);
    back.querySelector(".flow").textContent = ABOUT_FLOW[app];
    back.querySelector(".screen").textContent = ABOUT_SCREEN[app][lang];
    back.querySelector(".limits").innerHTML =
      ABOUT_TEXT.limits[lang].map(line => `<li>${line}</li>`).join("");
    for (const b of back.querySelectorAll(".mv-lang button"))
      b.setAttribute("aria-pressed", String(b.dataset.lang === lang));
    if (trigger) trigger.textContent = "ⓘ " + t("open", lang);
    back.querySelector(".x").setAttribute("aria-label", t("close", lang));
    document.documentElement.lang = lang;
  }

  function setLang(next) {
    if(window.floorI18n){window.floorI18n.setLanguage(next);return;}
    lang = next;
    try { localStorage.setItem(ABOUT_LANG_KEY, next); }
    catch (e) { /* a blocked store costs the preference, not the panel */ }
    render();
  }

  const open = () => { back.hidden = false; };
  const close = () => { back.hidden = true; };

  back.addEventListener("click", e => { if (e.target === back) close(); });
  back.querySelector(".x").onclick = close;
  for (const b of back.querySelectorAll(".mv-lang button"))
    b.onclick = () => setLang(b.dataset.lang);
  addEventListener("keydown", e => { if (e.key === "Escape" && !back.hidden) close(); });

  const trigger = document.createElement("button");
  window.addEventListener('floor-language-change',()=>{lang=window.floorI18n.lang;render();});
  trigger.className = "mv-about-btn";
  trigger.onclick = open;
  render();
  return trigger;
}
