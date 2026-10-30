import { formatMoney, humanize, isOverdue } from "@/lib/format";

describe("format", () => {
  it("formats AUD", () => expect(formatMoney(7900)).toContain("79.00"));
  it("humanizes keys", () => expect(humanize("senior_manager")).toBe("Senior Manager"));
  it("detects overdue dates", () => {
    expect(isOverdue("2000-01-01")).toBe(true);
    expect(isOverdue(null)).toBe(false);
  });
});
