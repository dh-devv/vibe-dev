import { useEffect, useState } from "react";
import type { Beat, CaseInput, Speaker, Verdict } from "../../types";
import { ApiError, runTrial } from "../../api/trial";
import { AiBadge } from "../../components/Common";
import { Person } from "../../components/PixelArt";

interface Props {
  input: CaseInput;
  onFinish: (verdict: Verdict, submittedAt: string) => void;
  onExit: () => void;
}

const NAMES: Record<Speaker, string> = {
  judge: "판사",
  defense: "변호인",
  prosecution: "검사"
};

const STAGES = ["변호인 변론", "검사 반박", "변호인 재반박", "판사 정리"] as const;

// 위에서 내려다본 법정 배치. 좌표는 무대 크기에 대한 퍼센트다.
const ACTORS: { id: string; speaker: Speaker; x: number; y: number }[] = [
  { id: "judge", speaker: "judge", x: 50, y: 12 },
  { id: "defense", speaker: "defense", x: 33, y: 66 },
  { id: "prosecution", speaker: "prosecution", x: 67, y: 66 }
];

export function Courtroom({ input, onFinish, onExit }: Props) {
  const [beats, setBeats] = useState<Beat[]>([]);
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [submittedAt, setSubmittedAt] = useState(() => new Date().toISOString());
  const [error, setError] = useState<ApiError | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    const ctrl = new AbortController();
    setBeats([]);
    setVerdict(null);
    setError(null);
    setIdx(0);
    (async () => {
      try {
        for await (const ev of runTrial(input, { signal: ctrl.signal })) {
          if (ev.type === "started") setSubmittedAt(ev.submittedAt);
          else if (ev.type === "beat") setBeats((b) => [...b, ev.beat]);
          else if (ev.type === "beat_delta") {
            setBeats((current) => {
              const existing = current.find((item) => item.n === ev.n);
              if (existing) {
                return current.map((item) =>
                  item.n === ev.n ? { ...item, text: item.text + ev.delta, complete: false } : item
                );
              }
              return [...current, {
                n: ev.n,
                speaker: ev.speaker,
                stage: ev.stage,
                text: ev.delta,
                complete: false
              }];
            });
          } else if (ev.type === "beat_finish") {
            setBeats((current) =>
              current.map((item) => item.n === ev.n ? { ...item, complete: true } : item)
            );
          } else setVerdict(ev.verdict);
        }
      } catch (e) {
        if (ctrl.signal.aborted) return;
        setError(e instanceof ApiError ? e : new ApiError("UNKNOWN", "재판 중 문제가 생겼습니다. 다시 시도해 주세요.", true));
      }
    })();
    return () => ctrl.abort();
  }, [input, attempt]);

  const beat = beats[idx];
  const hasNext = idx < beats.length - 1;
  const last = verdict !== null && idx >= beats.length;
  const speaker: Speaker = last ? "judge" : beat?.speaker ?? "defense";
  const text = last ? verdict.summary : beat?.text ?? "";

  const next = () => {
    if (beat?.complete && hasNext) setIdx(idx + 1);
    else if (beat?.complete && verdict) setIdx(beats.length);
    else if (last && verdict) onFinish(verdict, submittedAt);
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

  const stageName = last ? STAGES[3] : beat?.stage ?? STAGES[0];
  const activeId = speaker;
  const nameText = NAMES[speaker];
  const canAdvance = Boolean(
    (beat?.complete && (hasNext || idx === beats.length - 1 && verdict !== null)) || last
  );

  return (
    <main className="screen court">
      <ol className="stagebar" aria-label="맞춤 방안 도출 단계">
        {STAGES.map((s) => (
          <li key={s} className={s === stageName ? "on" : ""} aria-current={s === stageName ? "step" : undefined}>
            {s}
          </li>
        ))}
      </ol>

      <div className="stage" role="img" aria-label="재판소를 위에서 내려다본 모습. 위쪽에 판사, 아래쪽에 변호인과 검사가 있습니다.">
        <div className="furn bench"><span>재판장석</span></div>
        <div className="furn table def"><span>변호인석</span></div>
        <div className="furn table pro"><span>검사석</span></div>
        <div className="furn rail" />
        <div className="furn decor flag" />
        <div className="furn decor shelf" />
        {ACTORS.map((a) => {
          const active = a.id === activeId;
          return (
            <div key={a.id} className={active ? "actor active" : "actor"} style={{ left: `${a.x}%`, top: `${a.y}%` }}>
              {active && <span className="bubble" aria-hidden="true">…</span>}
              <Person speaker={a.speaker} className="sprite" />
            </div>
          );
        })}
      </div>

      <section className="px-box dialog" aria-label="자막">
        <div className="nameplate">
          {(beat || last) && <span>{last ? "공방을 정리한 판사" : nameText}</span>}
          {(beat || last) && <AiBadge />}
        </div>
        {text && <p className="speech" aria-hidden="true">{text}</p>}
        <p className="sr-only" aria-live="polite">{(beat?.complete || last) && text ? `${nameText}: ${text}` : ""}</p>

        {(beat || last) && (
          <button className="px-btn primary next" onClick={next} disabled={!canAdvance}>
            {last
              ? "최적 방안 보기 ▶"
              : canAdvance
                ? idx === beats.length - 1 ? "판사 정리 보기 ▶" : "다음 발언 ▶"
                : beat?.complete ? "판결 정리를 기다리는 중…" : "발언 생성 중…"}
          </button>
        )}
      </section>
    </main>
  );
}
