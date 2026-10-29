import { fireEvent, render, screen } from "@testing-library/react";

import { WorkspaceShell } from "./workspace-shell";

describe("WorkspaceShell", () => {
  it("renders the primary Mosaic workspace surfaces", () => {
    render(<WorkspaceShell />);

    expect(screen.getByLabelText("Mosaic home")).toBeInTheDocument();
    expect(screen.getByLabelText("Chat and control")).toBeInTheDocument();
    expect(screen.getByLabelText("Knowledge workspace")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Sources" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("switches inspector tabs and submits a local chat message", () => {
    render(<WorkspaceShell />);

    fireEvent.click(screen.getByRole("tab", { name: "Memory" }));
    expect(screen.getByText("Project memory")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Message Mosaic"), {
      target: { value: "What supports the launch positioning?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(screen.getByText("What supports the launch positioning?")).toBeInTheDocument();
  });
});
