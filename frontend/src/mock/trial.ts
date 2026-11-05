import type { Beat, Cause, CaseInput, Verdict } from "../types";

// 서버가 완성되기 전에 화면을 만들기 위한 가짜 데이터다. 배포 전에 이 폴더를 삭제한다.
// 배심원·사용자 발언·재판 이름은 PRD와 API_SPEC에 아직 없다. 문서 합의 뒤에 서버와 연결한다.
// 이 파일의 문장은 AI가 만든 것이 아니라 고정된 틀이다.

export const STAGES = ["개정", "변론", "반박", "진술", "협의", "선고"] as const;
export const USER_SPEECH_MAX = 200;

const clip = (s: string, n: number): string => {
  const chars = Array.from(s.trim());
  return chars.length > n ? chars.slice(0, n).join("") + "…" : chars.join("");
};

export function detectCause(input: CaseInput): Cause {
  const t = `${input.caseText} ${input.reason}`;
  if (/완벽|마음에 들|고치기만/.test(t)) return "완벽주의";
  if (/지쳐|피곤|피로|체력|힘이 없/.test(t)) return "피로";
  if (/시간이 (없|나지|부족)|바빠|바쁘/.test(t)) return "시간 부족";
  if (/재미|흥미|지루|의미/.test(t)) return "흥미 상실";
  return "막막함";
}

const CAUSE_LINE: Record<Cause, string> = {
  막막함: "무엇부터 해야 할지 길이 보이지 않아서",
  완벽주의: "완벽하게 해내고 싶은 마음이 너무 커서",
  "흥미 상실": "일이 재미없고 의미를 찾지 못해서",
  "시간 부족": "쓸 수 있는 시간이 실제로 부족해서",
  피로: "몸과 마음이 지쳐 있어서"
};

export function makeBeats(input: CaseInput, userSpeech: string | null): Beat[] {
  const cause = detectCause(input);
  const reason = clip(input.reason, 60);
  const topic = clip(input.caseText, 50);
  const said = userSpeech && userSpeech.trim() ? clip(userSpeech, 50) : "";
  const dl = input.deadline ? `마감은 ${input.deadline}입니다. 하루하루가 줄어듭니다.` : "마감이 없다는 이유로 무한정 미룰 수는 없습니다.";
  return [
    { speaker: "judge", stage: "개정", ai: true, text: `개정합니다. 사건 「${clip(input.title, 24)}」을 심리합니다. 피고인은 "${topic}" 상태로 일을 미루고 있습니다.` },
    { speaker: "defense", stage: "변론", ai: true, text: `재판장님, 피고인이 미룬 이유는 "${reason}"입니다. 게으름이 아니라 ${CAUSE_LINE[cause]} 멈춘 것입니다. 시작이 쉬웠다면 이미 했을 것입니다.` },
    { speaker: "prosecution", stage: "반박", ai: true, text: `변호인의 말에 반박합니다. "${reason}"라는 사정이 있어도 미룬 값은 계속 쌓입니다. ${dl} 이유를 알면서도 움직이지 않은 책임이 있습니다.` },
    { speaker: "judge", stage: "진술", ai: true, text: "피고인, 직접 하실 말씀이 있으면 발언하세요. 생략해도 됩니다." },
    { speaker: "user", stage: "진술", ai: false, text: said ? said : "(발언을 생략했습니다.)" },
    { speaker: "defense", stage: "반박", ai: true, text: `검사가 말한 비용은 인정합니다. 그러나 피고인은 방금 ${said ? `"${said}"라고 ` : ""}직접 입장을 밝혔고, 작게 시작할 의지가 있습니다. 시작 부담부터 낮추면 됩니다.` },
    { speaker: "judge", stage: "협의", ai: true, text: "양측 발언을 모두 들었습니다. 배심원단과 협의하겠습니다." },
    { speaker: "jury", seat: 0, stage: "협의", ai: true, text: `배심원 1: 변호인이 말한 "${CAUSE_LINE[cause]}"라는 설명에 공감이 갑니다.` },
    { speaker: "jury", seat: 2, stage: "협의", ai: true, text: "배심원 3: 검사의 지적도 맞습니다. 비용을 줄이는 작은 약속이 필요해 보입니다." },
    { speaker: "judge", stage: "선고", ai: true, text: "협의를 마쳤습니다. 판결을 선고합니다." }
  ];
}

const TABLE: Record<Cause, Omit<Verdict, "cause" | "evidence">> = {
  막막함: {
    summary: "변호인이 말한 막막함은 받아들이고, 검사가 지적한 비용은 일부만 받아들입니다.",
    prescriptions: [
      { title: "목차부터 만들기", steps: ["제목을 한 줄로 적는다", "소제목 3개를 적는다"], minutes: 15, reason: "시작이 막막하다는 변론에 맞춰 첫 단계를 작게 나누었습니다." },
      { title: "5분만 열어 보기", steps: ["타이머를 5분에 맞춘다", "5분 동안 아무 문장이나 쓴다", "멈춰도 좋다고 스스로 허락한다"], minutes: 5, reason: "시작 저항을 낮추는 시간 상자입니다." }
    ]
  },
  완벽주의: {
    summary: "완벽하게 하려는 마음이 시작을 막는다는 변론을 받아들이고, 기준을 낮추라는 검사의 지적을 따릅니다.",
    prescriptions: [
      { title: "엉망인 초안 허락하기", steps: ["첫 문장을 고치지 않고 이어 쓴다", "20분 동안 지우개를 쓰지 않는다"], minutes: 20, reason: "고치기 전에 쓰기부터 하도록 순서를 바꿨습니다." },
      { title: "합격선 정하기", steps: ["이 일의 최소 합격선을 한 줄로 쓴다", "합격선만 채우고 저장한다"], minutes: 10, reason: "일부는 포기해도 된다는 기준을 먼저 세웁니다." }
    ]
  },
  "흥미 상실": {
    summary: "재미가 없다는 변론을 받아들이고, 보상 없이 버티기는 어렵다는 점을 인정합니다.",
    prescriptions: [
      { title: "끝나면 주는 작은 상", steps: ["끝나고 할 즐거운 일을 하나 정한다", "25분만 집중하고 상을 받는다"], minutes: 25, reason: "흥미가 낮은 일에는 보상 설계가 필요합니다." },
      { title: "장소 바꿔 시작하기", steps: ["평소와 다른 자리로 옮긴다", "자리에서 첫 문장을 쓴다"], minutes: 10, reason: "환경을 바꿔 시작 신호를 새로 만듭니다." }
    ]
  },
  "시간 부족": {
    summary: "시간이 부족하다는 변론은 사실로 보고, 쓸 수 있는 틈에 맞춰 일을 줄입니다.",
    prescriptions: [
      { title: "틈새 15분 확보", steps: ["오늘 비는 시간을 달력에서 찾는다", "그 15분에 첫 단계 하나만 한다"], minutes: 15, reason: "큰 덩어리 대신 작은 틈에 일을 배치합니다." },
      { title: "마감 앞당기기", steps: ["내 마감을 하루 앞으로 정한다", "남은 일을 3조각으로 나눈다"], minutes: 10, reason: "여유 없이 밀리는 것을 막습니다." }
    ]
  },
  피로: {
    summary: "지친 상태라는 변론을 받아들이고, 먼저 쉬고 나서 작게 시작하도록 처방합니다.",
    prescriptions: [
      { title: "10분 쉬고 시작하기", steps: ["10분 동안 눈을 감고 쉰다", "쉰 뒤 첫 단계만 한다"], minutes: 10, reason: "쉬고 나서 하라는 처방입니다. 컨디션이 계속 나쁘면 전문가와 상의하세요." },
      { title: "가장 쉬운 일 하나", steps: ["오늘 할 일 중 가장 쉬운 것을 고른다", "그것만 끝내고 오늘을 마친다"], minutes: 15, reason: "일부는 내일로 미루는 것을 허락합니다." }
    ]
  }
};

export function makeVerdict(input: CaseInput): Verdict {
  const cause = detectCause(input);
  return { ...TABLE[cause], cause, evidence: [1, 2] };
}

const CRISIS_WORDS = ["자살", "자해", "죽고싶", "죽고 싶", "극단적선택", "극단적 선택"];
// 위기 신호의 실제 검사는 서버(src/app/safety.py)가 한다. 이것은 화면 확인용 흉내다.
export function mockCrisisCheck(text: string): boolean {
  const t = text.replace(/\s+/g, "").toLowerCase();
  return CRISIS_WORDS.some((w) => t.includes(w.replace(/\s+/g, "")));
}

export const HELPLINES = [
  { name: "자살예방 상담전화", phone: "109", hours: "24시간" },
  { name: "정신건강 위기상담전화", phone: "1577-0199", hours: "24시간" },
  { name: "긴급 상황", phone: "119", hours: "24시간" }
];
