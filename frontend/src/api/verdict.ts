import type { Cause, Verdict } from "../types";

export const CAUSES: Cause[] = ["막막함", "완벽주의", "흥미 상실", "시간 부족", "피로"];

const len = (s: string): number => Array.from(s).length;
const inRange = (s: unknown, min: number, max: number): s is string =>
  typeof s === "string" && len(s) >= min && len(s) <= max;

// API_SPEC 4.5절(판결문) 규칙을 그대로 검사한다. 서버 검증을 대체하지 않는다.
export function isVerdict(v: unknown): v is Verdict {
  if (!v || typeof v !== "object") return false;
  const o = v as Record<string, unknown>;
  if (!inRange(o.summary, 1, 400)) return false;
  if (!CAUSES.includes(o.cause as Cause)) return false;
  const pres = o.prescriptions;
  if (!Array.isArray(pres) || pres.length < 1 || pres.length > 2) return false;
  const okPres = pres.every((p) => {
    if (!p || typeof p !== "object") return false;
    const q = p as Record<string, unknown>;
    return (
      inRange(q.title, 1, 30) &&
      Array.isArray(q.steps) &&
      q.steps.length >= 2 &&
      q.steps.length <= 4 &&
      q.steps.every((s) => inRange(s, 1, 80)) &&
      Number.isInteger(q.minutes) &&
      (q.minutes as number) >= 5 &&
      (q.minutes as number) <= 120 &&
      inRange(q.reason, 1, 150)
    );
  });
  if (!okPres) return false;
  const ev = o.evidence;
  return (
    Array.isArray(ev) &&
    ev.length >= 1 &&
    ev.length <= 3 &&
    ev.every((n) => Number.isInteger(n) && (n as number) >= 1 && (n as number) <= 3) &&
    new Set(ev).size === ev.length
  );
}

export const charCount = len;
