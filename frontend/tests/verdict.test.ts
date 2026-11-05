import { describe, expect, it } from "vitest";
import { isVerdict } from "../src/api/verdict";
import { makeVerdict } from "../src/mock/trial";

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
  it("목업 판결문이 형식을 지키고 사건마다 처방 제목이 다르다", () => {
    const mk = (caseText: string, reason: string) => makeVerdict({ title: "t", caseText, reason, deadline: null });
    const a = mk("보고서를 못 쓴다", "무엇부터 할지 몰라서 막막하다");
    const b = mk("시험 공부를 못 한다", "너무 지쳐서 힘이 없다");
    const c = mk("자소서를 고치기만 한다", "완벽하게 쓰고 싶다");
    [a, b, c].forEach((v) => expect(isVerdict(v)).toBe(true));
    expect(new Set([a, b, c].map((v) => v.prescriptions[0].title)).size).toBe(3);
  });
});
