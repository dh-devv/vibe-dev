import { useEffect, useMemo, useRef, useState } from "react";
import type { Beat, CaseInput, Speaker, Verdict } from "../../types";
import { charCount } from "../../api/verdict";
import { ApiError, runTrial } from "../../api/trial";
import { STAGES, USER_SPEECH_MAX } from "../../mock/trial";
import { AiBadge } from "../../components/Common";
import { Person } from "../../components/PixelArt";

interface Props {
  input: CaseInput;
  onFinish: (verdict: Verdict, submittedAt: string) => void;
  onExit: () => void;
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

export function Courtroom({ input, onFinish, onExit }: Props) {
  const [beats, setBeats] = useState<Beat[]>([]);
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [submittedAt, setSubmittedAt] = useState(() => new Date().toISOString());
  const [error, setError] = useState<ApiError | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [asking, setAsking] = useState(false);
  const [draft, setDraft] = useState("");
  const [idx, setIdx] = useState(0);
  const resolveSpeech = useRef<((v: string) => void) | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    setBeats([]);
    setVerdict(null);
    setError(null);
    setIdx(0);
    setAsking(false);
    const askUser = () =>
      new Promise<string>((resolve) => {
        resolveSpeech.current = resolve;
        setAsking(true);
      });
    (async () => {
      try {
        for await (const ev of runTrial(input, { signal: ctrl.signal, askUser })) {
          if (ev.type === "started") setSubmittedAt(ev.submittedAt);
          else if (ev.type === "beat") setBeats((b) => [...b, ev.beat]);
          else setVerdict(ev.verdict);
        }
      } catch (e) {
        if (ctrl.signal.aborted) return;
        setError(e instanceof ApiError ? e : new ApiError("UNKNOWN", "재판 중 문제가 생겼습니다. 다시 시도해 주세요.", true));
      }
    })();
    return () => ctrl.abort();
  }, [input, attempt]);

  const beat = beats[idx];
  const text = beat?.text ?? "재판관이 사건을 살펴보고 있습니다…";
  const speaker: Speaker = beat?.speaker ?? "judge";
  const typed = useTypewriter(text);
  const hasNext = idx < beats.length - 1;
  const last = verdict !== null && !hasNext;
  const showForm = asking && !hasNext && typed.done;

  const next = () => {
    if (!typed.done) {
      typed.skip();
      return;
    }
    if (hasNext) setIdx(idx + 1);
    else if (verdict) onFinish(verdict, submittedAt);
  };

  const submitSpeech = (value: string) => {
    resolveSpeech.current?.(value.trim());
    resolveSpeech.current = null;
    setAsking(false);
    setDraft("");
  };

  if (error) {
    return (
      <main className="screen court">
        <section className="px-box crisis" role="alert">
          <h2 className="box-title">{error.code === "CRISIS_SIGNAL" ? "재판보다 도움이 먼저입니다" : "재판을 마치지 못했습니다"}</h2>
          <p>{error.message}</p>
          {error.helplines.length > 0 && (
            <ul>
              {error.helplines.map((h) => (
                <li key={h.phone}>{h.name} {h.phone} ({h.hours})</li>
              ))}
            </ul>
          )}
          <div className="row">
            {error.retryable && <button className="px-btn primary" onClick={() => setAttempt(attempt + 1)}>다시 시도</button>}
            <button className="px-btn" onClick={onExit}>사건 다시 쓰기</button>
          </div>
        </section>
      </main>
    );
  }

  const stageName = beat?.stage ?? STAGES[0];
  const activeId = speaker === "jury" ? `jury${beat?.seat ?? 0}` : speaker;
  const nameText = speaker === "jury" ? `배심원 ${(beat?.seat ?? 0) + 1}` : NAMES[speaker];

  return (
    <main className="screen court">
      <ol className="stagebar" aria-label="재판 진행 단계">
        {STAGES.map((s) => (
          <li key={s} className={s === stageName ? "on" : ""} aria-current={s === stageName ? "step" : undefined}>
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
          {beat?.ai && <AiBadge />}
        </div>
        <p className="speech" aria-hidden="true">{typed.shown}</p>
        <p className="sr-only" aria-live="polite">{typed.done ? `${nameText}: ${text}` : ""}</p>

        {showForm ? (
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
          <button className="px-btn primary next" onClick={next} disabled={typed.done && !hasNext && !verdict}>
            {!typed.done ? "건너뛰기 ▶▶" : last ? "판결 듣기 ▶" : hasNext ? "다음 ▶" : "판사가 생각 중…"}
          </button>
        )}
      </section>
    </main>
  );
}
