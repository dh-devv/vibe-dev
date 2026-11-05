import { useEffect, useMemo, useState } from "react";
import type { CaseInput, Speaker } from "../../types";
import { charCount } from "../../api/verdict";
import { STAGES, USER_SPEECH_MAX, makeBeats } from "../../mock/trial";
import { AiBadge } from "../../components/Common";
import { Person } from "../../components/PixelArt";

interface Props {
  input: CaseInput;
  onFinish: (userSpeech: string) => void;
}

const NAMES: Record<Speaker, string> = {
  judge: "판사",
  jury: "배심원",
  defense: "변호사",
  prosecution: "검사",
  user: "나(피고인)"
};

// 위에서 내려다본 법정 배치. 좌표는 무대 크기에 대한 퍼센트다.
const ACTORS: { id: string; speaker: Speaker; seat?: number; x: number; y: number }[] = [
  { id: "judge", speaker: "judge", x: 50, y: 12 },
  { id: "jury0", speaker: "jury", seat: 0, x: 13, y: 33 },
  { id: "jury1", speaker: "jury", seat: 1, x: 13, y: 45 },
  { id: "jury2", speaker: "jury", seat: 2, x: 13, y: 57 },
  { id: "jury3", speaker: "jury", seat: 3, x: 13, y: 69 },
  { id: "defense", speaker: "defense", x: 33, y: 66 },
  { id: "prosecution", speaker: "prosecution", x: 67, y: 66 },
  { id: "user", speaker: "user", x: 50, y: 80 }
];

function useTypewriter(text: string) {
  const reduce = useMemo(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches, []);
  const chars = useMemo(() => Array.from(text), [text]);
  const [n, setN] = useState(reduce ? chars.length : 0);

  useEffect(() => {
    if (reduce) {
      setN(chars.length);
      return;
    }
    setN(0);
    const id = window.setInterval(() => {
      setN((v) => {
        if (v >= chars.length) {
          window.clearInterval(id);
          return v;
        }
        return v + 1;
      });
    }, 28);
    return () => window.clearInterval(id);
  }, [chars, reduce]);

  return { shown: chars.slice(0, n).join(""), done: n >= chars.length, skip: () => setN(chars.length) };
}

export function Courtroom({ input, onFinish }: Props) {
  const [userSpeech, setUserSpeech] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [idx, setIdx] = useState(0);

  const beats = useMemo(() => makeBeats(input, userSpeech), [input, userSpeech]);
  const beat = beats[idx];
  const waitingUser = beat.speaker === "user" && userSpeech === null;
  const text = waitingUser ? "피고인, 직접 하실 말씀이 있으면 발언하세요. 생략해도 됩니다." : beat.text;
  const speaker: Speaker = beat.speaker;
  const typed = useTypewriter(text);
  const last = idx === beats.length - 1;

  const next = () => {
    if (!typed.done) {
      typed.skip();
      return;
    }
    if (last) onFinish(userSpeech ?? "");
    else setIdx(idx + 1);
  };

  const submitSpeech = (value: string) => {
    setUserSpeech(value.trim());
    setDraft("");
  };

  const activeId = speaker === "jury" ? `jury${beat.seat ?? 0}` : speaker;
  const nameText = speaker === "jury" ? `배심원 ${(beat.seat ?? 0) + 1}` : NAMES[speaker];

  return (
    <main className="screen court">
      <ol className="stagebar" aria-label="재판 진행 단계">
        {STAGES.map((s) => (
          <li key={s} className={s === beat.stage ? "on" : ""} aria-current={s === beat.stage ? "step" : undefined}>
            {s}
          </li>
        ))}
      </ol>

      <div className="stage" role="img" aria-label="재판소를 위에서 내려다본 모습. 가운데 위에 판사, 왼쪽에 배심원, 가운데 아래에 변호사와 검사와 피고인이 있습니다.">
        <div className="furn bench"><span>재판장석</span></div>
        <div className="furn jurybox"><span>배심원석</span></div>
        <div className="furn table def"><span>변호인석</span></div>
        <div className="furn table pro"><span>검사석</span></div>
        <div className="furn stand"><span>피고인석</span></div>
        <div className="furn rail" />
        <div className="furn decor flag" />
        <div className="furn decor shelf" />
        {ACTORS.map((a) => {
          const active = a.id === activeId;
          return (
            <div key={a.id} className={active ? "actor active" : "actor"} style={{ left: `${a.x}%`, top: `${a.y}%` }}>
              {active && <span className="bubble" aria-hidden="true">…</span>}
              <Person speaker={a.speaker} seat={a.seat} className="sprite" />
            </div>
          );
        })}
      </div>

      <section className="px-box dialog" aria-label="자막">
        <div className="nameplate">
          <span>{nameText}</span>
          {beat.ai && <AiBadge />}
        </div>
        <p className="speech" aria-hidden="true">{typed.shown}</p>
        <p className="sr-only" aria-live="polite">{typed.done ? `${nameText}: ${text}` : ""}</p>

        {waitingUser ? (
          <div className="speak-form">
            <label htmlFor="speech">피고인 발언 (최대 {USER_SPEECH_MAX}자)</label>
            <textarea id="speech" className="px-input" rows={3} value={draft} onChange={(e) => setDraft(e.target.value)} />
            <p className="hint">{charCount(draft)}/{USER_SPEECH_MAX}</p>
            <div className="row">
              <button className="px-btn primary" disabled={charCount(draft.trim()) < 1 || charCount(draft) > USER_SPEECH_MAX} onClick={() => submitSpeech(draft)}>
                발언하기
              </button>
              <button className="px-btn" onClick={() => submitSpeech("")}>발언 생략</button>
            </div>
          </div>
        ) : (
          <button className="px-btn primary next" onClick={next}>
            {typed.done ? (last ? "판결 듣기 ▶" : "다음 ▶") : "건너뛰기 ▶▶"}
          </button>
        )}
      </section>
    </main>
  );
}
