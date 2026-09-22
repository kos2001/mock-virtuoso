/* The introduction panel, shared by the workbench and the design floor.
 *
 * One copy, two hosts: each page calls mountAbout() with its own id and gets
 * the shared explanation plus the paragraph about itself. Korean and English
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
      "레이아웃 도메인만 다룹니다. schematic·Maestro 함수는 구현돼 있지 않습니다.",
      "SKILL의 부분집합입니다. 없는 함수는 nil을 돌려주지 않고 소리 내어 실패합니다.",
      "DRC·LVS·시뮬레이션은 없습니다. 도형은 눈에 보이는 것일 뿐 검증된 것이 아닙니다.",
      "기술 파일은 작고 고정돼 있습니다 — 레이어 7종, via 정의 4종.",
    ],
    en: [
      "The layout domain only. Schematic and Maestro functions are not implemented.",
      "A subset of SKILL. A function it lacks fails loudly instead of returning nil.",
      "No DRC, no LVS, no simulation. Geometry is drawn, not verified.",
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
  workbench: {
    ko: "레이아웃 워크벤치입니다. 여기서는 사람이 직접 운전합니다 — 셀을 만들고, 인스턴스를 배치하고, " +
        "영역을 선택하고, SKILL을 직접 보냅니다. 버튼 하나하나가 브리지 호출로 나가고, " +
        "캔버스는 디자인 DB를 다시 읽어 그립니다.",
    en: "The layout workbench. You drive it — build cells, place instances, select an area, send " +
        "SKILL by hand. Every button goes out as a bridge call, and the canvas is drawn from a " +
        "read-back of the design database.",
  },
  floor: {
    ko: "에이전트 설계 현장입니다. 사람이 아니라 에이전트들이 운전하고, 이 화면은 그 과정을 " +
        "지켜봅니다. 각 에이전트는 자기 레인 — 데몬 포트 앞에 선 기록용 프록시 — 을 통해 붙습니다. " +
        "기록은 mock 안이 아니라 전선 위에서 이뤄지므로, 여기 보이는 모든 줄은 진짜 Virtuoso가 " +
        "받았을 바로 그 SKILL입니다.",
    en: "The agent design floor. Agents drive, not you, and this screen watches them. Each agent " +
        "connects through its own lane — a recording proxy standing where the daemon's port would " +
        "be. Recording happens on the wire rather than inside the mock, so every line here is " +
        "exactly the SKILL a real Virtuoso would have received.",
  },
};

const ABOUT_FLOW = {
  workbench: "you  →  virtuoso-bridge  →  TCP  →  mock-virtuoso  →  design database",
  floor:     "agent  →  virtuoso-bridge  →  lane (recording proxy)  →  mock-virtuoso  →  design database",
};

const ABOUT_CSS = `
.mv-about-btn{background:none;border:1px solid #30363d;color:#8b949e;border-radius:999px;
  padding:2px 11px;font:inherit;font-size:11px;cursor:pointer}
.mv-about-btn:hover{color:#e6edf3;border-color:#4493f8}
.mv-about-back{position:fixed;inset:0;background:rgba(2,5,10,.72);display:flex;
  align-items:center;justify-content:center;z-index:9999;padding:24px}
.mv-about-back[hidden]{display:none}
.mv-about{background:#0f151d;border:1px solid #263041;border-radius:10px;max-width:760px;
  width:100%;max-height:100%;overflow:auto;color:#c9d1d9;
  font:13px/1.65 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  box-shadow:0 18px 50px rgba(0,0,0,.55)}
.mv-about header{display:flex;align-items:center;gap:12px;padding:16px 20px;
  border-bottom:1px solid #1d2431;position:sticky;top:0;background:#0f151d}
.mv-about header img{width:26px;height:26px}
.mv-about h2{margin:0;font-size:15px;letter-spacing:.2px;color:#e6edf3}
.mv-about .grow{flex:1}
.mv-lang{display:flex;border:1px solid #30363d;border-radius:999px;overflow:hidden}
.mv-lang button{background:none;border:0;color:#8b949e;padding:3px 11px;font:inherit;
  font-size:11px;cursor:pointer}
.mv-lang button[aria-pressed="true"]{background:#1f6feb;color:#fff}
.mv-about .x{background:none;border:0;color:#8b949e;font:inherit;font-size:16px;
  cursor:pointer;padding:0 4px;line-height:1}
.mv-about .x:hover{color:#e6edf3}
.mv-about section{padding:16px 20px;border-bottom:1px solid #161d26}
.mv-about section:last-child{border-bottom:0}
.mv-about h3{margin:0 0 7px;font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;
  color:#6e7681;font-weight:600}
.mv-about p{margin:0}
.mv-about pre{margin:9px 0 0;padding:10px 12px;background:#0a0f16;border:1px solid #1d2431;
  border-radius:6px;color:#4493f8;font-size:11.5px;white-space:pre-wrap;word-break:break-word}
.mv-about ul{margin:0;padding-left:18px}
.mv-about li{margin:3px 0}
.mv-about a{color:#4493f8}
.mv-about .foot{display:flex;gap:8px;align-items:baseline;font-size:11.5px;color:#6e7681}
`;

function aboutLang() {
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
  trigger.className = "mv-about-btn";
  trigger.onclick = open;
  render();
  return trigger;
}
