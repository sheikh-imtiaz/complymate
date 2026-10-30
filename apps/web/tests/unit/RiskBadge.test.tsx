import { render, screen } from "@testing-library/react";
import { RiskBadge, StatusBadge } from "@/components/clients/RiskBadge";

describe("RiskBadge", () => {
  it("shows the level", () => {
    render(<RiskBadge level="high" />);
    expect(screen.getByText("High risk")).toBeInTheDocument();
  });
  it("shows not assessed", () => {
    render(<RiskBadge level={null} />);
    expect(screen.getByText("Not assessed")).toBeInTheDocument();
  });
  it("shows status", () => {
    render(<StatusBadge status="approved" />);
    expect(screen.getByText("Approved")).toBeInTheDocument();
  });
});
