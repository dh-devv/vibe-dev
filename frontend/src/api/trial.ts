import type { Beat, CaseInput, Helpline, Verdict } from "../types";
import { isVerdict } from "./verdict";

// 재판 한 번을 서버 이벤트 흐름으로 받는다.

export type TrialEvent =
  | { type: "started"; submittedAt: string }
  | { type: "beat"; beat: Beat }
  | { type: "beat_delta"; n: number; speaker: Beat["speaker"]; stage: string; delta: string }
  | { type: "beat_finish"; n: number }
  | { type: "verdict"; verdict: Verdict };

export interface TrialOptions {
  signal: AbortSignal;
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
const STAGE_LABEL: Record<string, string> = {
  defense: "변호인 변론",
  prosecution: "검사 반박",
  rebuttal: "변호인 재반박",
};
const SPEAKERS = new Set(["defense", "prosecution"]);

function toRequestBody(input: CaseInput) {
  return {
    case: input.caseText.trim(),
    reason: input.reason.trim(),
    deadline: input.deadline
  };
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
  const streamedStatements = new Map<number, string>();
  try {
    for await (const { event, data } of parseSse(res.body)) {
      const d = data as Record<string, unknown>;
      if (event === "trial_started") yield { type: "started", submittedAt: String(d.submittedAt) };
      else if (event === "stage") stage = String(d.stage);
      else if (event === "statement" && SPEAKERS.has(String(d.role))) {
        const n = Number(d.n);
        if (!Number.isInteger(n) || n < 1) continue;
        if (typeof d.delta !== "string") {
          throw new ApiError("STREAM_INVALID", "AI 발언 형식이 올바르지 않습니다.", false);
        }
        const speaker = d.role as Beat["speaker"];
        const label = STAGE_LABEL[stage] ?? "변호인 변론";
        streamedStatements.set(n, (streamedStatements.get(n) ?? "") + d.delta);
        yield { type: "beat_delta", n, speaker, stage: label, delta: d.delta };
      } else if (event === "statement_done" && SPEAKERS.has(String(d.role))) {
        const n = Number(d.n);
        if (!Number.isInteger(n) || n < 1) continue;
        if (typeof d.text !== "string") {
          throw new ApiError("STREAM_INVALID", "AI 발언 형식이 올바르지 않습니다.", false);
        }
        const streamedText = streamedStatements.get(n);
        if (streamedText !== undefined) {
          if (streamedText !== d.text) {
            throw new ApiError("STREAM_INVALID", "AI 발언 형식이 올바르지 않습니다.", false);
          }
          yield { type: "beat_finish", n };
        } else {
          yield {
            type: "beat",
            beat: {
              n,
              speaker: d.role as Beat["speaker"],
              stage: STAGE_LABEL[stage] ?? "변호인 변론",
              text: d.text,
              complete: true
            }
          };
        }
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

export function runTrial(input: CaseInput, options: TrialOptions): AsyncGenerator<TrialEvent> {
  return serverTrial(input, options);
}
