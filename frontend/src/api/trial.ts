import type { Beat, CaseInput, Helpline, Verdict } from "../types";
import { isVerdict } from "./verdict";

// 재판 한 번을 이벤트 흐름으로 받는다. 화면은 이 흐름만 알고, 문장이 AI에서 오는지 목업에서 오는지는 모른다.
// 실제 서버는 API_SPEC 5절을 따른다. 목업은 VITE_USE_MOCK=true일 때만 쓴다.

export type TrialEvent =
  | { type: "started"; submittedAt: string }
  | { type: "beat"; beat: Beat }
  | { type: "verdict"; verdict: Verdict };

export interface TrialOptions {
  signal: AbortSignal;
  // 목업 전용. 실제 서버에는 사용자 발언 요청이 아직 없다(문서 합의 전).
  askUser?: () => Promise<string>;
}

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public retryable: boolean,
    public helplines: Helpline[] = []
  ) {
    super(message);
  }
}

const TOTAL_TIMEOUT_MS = 90_000;
const STAGE_LABEL: Record<string, string> = { defense: "변론", prosecution: "반박", rebuttal: "반박" };
const SPEAKERS = new Set(["judge", "jury", "defense", "prosecution"]);

// API_SPEC은 case 하나(5~300자)만 받는다. 재판 이름과 사유를 합치는 방식은 합의 전이다.
function toRequestBody(input: CaseInput) {
  const merged = `${input.caseText.trim()} (미룬 이유: ${input.reason.trim()})`;
  return { case: Array.from(merged).slice(0, 300).join(""), deadline: input.deadline };
}

async function* parseSse(body: ReadableStream<Uint8Array>): AsyncGenerator<{ event: string; data: unknown }> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) return;
    buf += decoder.decode(value, { stream: true });
    let cut: number;
    while ((cut = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, cut);
      buf = buf.slice(cut + 2);
      let event = "";
      let data = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (event && data) yield { event, data: JSON.parse(data) };
    }
  }
}

async function toApiError(res: Response): Promise<ApiError> {
  try {
    const j = (await res.json()) as { code?: string; message?: string; retryable?: boolean; helplines?: Helpline[] };
    return new ApiError(j.code ?? "UNKNOWN", j.message ?? "요청을 처리하지 못했습니다.", Boolean(j.retryable), j.helplines ?? []);
  } catch {
    return new ApiError("UNKNOWN", "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.", true);
  }
}

async function* serverTrial(input: CaseInput, { signal }: TrialOptions): AsyncGenerator<TrialEvent> {
  const timed = AbortSignal.any([signal, AbortSignal.timeout(TOTAL_TIMEOUT_MS)]);
  let res: Response;
  try {
    res = await fetch("/api/trial", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(toRequestBody(input)),
      signal: timed
    });
  } catch {
    if (signal.aborted) return;
    throw new ApiError("NETWORK", "서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.", true);
  }
  if (!res.ok || !res.body) throw await toApiError(res);

  let stage = "";
  try {
    for await (const { event, data } of parseSse(res.body)) {
      const d = data as Record<string, unknown>;
      if (event === "trial_started") yield { type: "started", submittedAt: String(d.submittedAt) };
      else if (event === "stage") stage = String(d.stage);
      else if (event === "statement_done" && SPEAKERS.has(String(d.role))) {
        yield { type: "beat", beat: { speaker: d.role as Beat["speaker"], stage: STAGE_LABEL[stage] ?? "변론", text: String(d.text), ai: true } };
      } else if (event === "verdict") {
        if (!isVerdict(d)) throw new ApiError("VERDICT_INVALID", "판결문을 만들지 못했습니다. 다시 시도해 주세요.", true);
        yield { type: "verdict", verdict: d };
      } else if (event === "error") {
        throw new ApiError(String(d.code), String(d.message), Boolean(d.retryable));
      }
    }
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if (signal.aborted) return;
    throw new ApiError("TIMEOUT", "재판이 중단되었습니다. 다시 시도해 주세요.", true);
  }
}

async function* mockTrial(input: CaseInput, { signal, askUser }: TrialOptions): AsyncGenerator<TrialEvent> {
  const { makeBeats, makeVerdict } = await import("../mock/trial");
  const wait = (ms: number) => new Promise<void>((r) => window.setTimeout(r, ms));
  yield { type: "started", submittedAt: new Date().toISOString() };
  let beats = makeBeats(input, null);
  for (let i = 0; i < beats.length; i++) {
    if (signal.aborted) return;
    await wait(700);
    yield { type: "beat", beat: beats[i] };
    if (beats[i].speaker === "judge" && beats[i + 1]?.speaker === "user" && askUser) {
      beats = makeBeats(input, await askUser());
    }
  }
  yield { type: "verdict", verdict: makeVerdict(input) };
}

export function runTrial(input: CaseInput, options: TrialOptions): AsyncGenerator<TrialEvent> {
  return import.meta.env.VITE_USE_MOCK === "true" ? mockTrial(input, options) : serverTrial(input, options);
}
