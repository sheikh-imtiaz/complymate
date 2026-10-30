import { can, scopeFor } from "@/lib/permissions";

describe("permissions", () => {
  const staff = ["client:create", "client:read:own", "smr:create_draft"];
  it("resolves scopes like the API", () => {
    expect(scopeFor(staff, "client:read")).toBe("own");
    expect(scopeFor(staff, "client:create")).toBe("all");
    expect(scopeFor(staff, "smr:read")).toBeNull();
  });
  it("can() is true for any scope", () => {
    expect(can(staff, "client:read")).toBe(true);
    expect(can(["program:read:shared"], "program:read")).toBe(true);
    expect(can(undefined, "client:read")).toBe(false);
  });
});
