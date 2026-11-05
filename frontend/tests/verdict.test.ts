import { describe, expect, it } from "vitest";
import { isVerdict } from "../src/api/verdict";

const base = {
  summary: "요지",
  cause: "막막함",
  prescriptions: [{ title: "제목", steps: ["하나", "둘"], minutes: 10, reason: "이유" }],
  evidence: [1, 2]
};

describe("판결문 검증", () => {
  it("올바른 판결문을 통과시킨다", () => {
    expect(isVerdict(base)).toBe(true);
  });
  it("근거 번호가 1~3 밖이면 거부한다", () => {
    expect(isVerdict({ ...base, evidence: [0] })).toBe(false);
    expect(isVerdict({ ...base, evidence: [4] })).toBe(false);
    expect(isVerdict({ ...base, evidence: [1, 1] })).toBe(false);
  });
  it("원인이 목록 밖이면 거부한다", () => {
    expect(isVerdict({ ...base, cause: "게으름" })).toBe(false);
  });
});
