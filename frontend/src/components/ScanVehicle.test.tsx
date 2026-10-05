import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ScanVehicle } from "./ScanVehicle";

function fakeStream(): MediaStream {
  return { getTracks: () => [{ stop: vi.fn() }] } as unknown as MediaStream;
}

afterEach(() => {
  Object.defineProperty(navigator, "mediaDevices", { value: undefined, configurable: true });
});

describe("ScanVehicle", () => {
  it("shows an unsupported message when the camera API is unavailable", () => {
    render(<ScanVehicle />);
    expect(screen.getByText(/camera isn't available/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /scan vehicle/i })).not.toBeInTheDocument();
  });

  it("requests access and shows the live preview with capture/cancel controls", async () => {
    Object.defineProperty(navigator, "mediaDevices", {
      value: { getUserMedia: vi.fn(async () => fakeStream()) },
      configurable: true,
    });
    const user = userEvent.setup();
    render(<ScanVehicle />);

    await user.click(screen.getByRole("button", { name: /scan vehicle/i }));

    expect(await screen.findByRole("button", { name: /capture/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
  });

  it("shows a denial message when the user refuses camera permission", async () => {
    Object.defineProperty(navigator, "mediaDevices", {
      value: {
        getUserMedia: vi.fn(async () => {
          throw new DOMException("denied", "NotAllowedError");
        }),
      },
      configurable: true,
    });
    const user = userEvent.setup();
    render(<ScanVehicle />);

    await user.click(screen.getByRole("button", { name: /scan vehicle/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/denied/i);
  });

  it("never claims to analyze a captured photo -- only the honest unavailable copy", async () => {
    Object.defineProperty(navigator, "mediaDevices", {
      value: { getUserMedia: vi.fn(async () => fakeStream()) },
      configurable: true,
    });
    const user = userEvent.setup();
    render(<ScanVehicle />);
    await user.click(screen.getByRole("button", { name: /scan vehicle/i }));
    await user.click(await screen.findByRole("button", { name: /capture/i }));

    expect(await screen.findByText(/image analysis isn't available in this prototype yet/i)).toBeInTheDocument();
    expect(screen.queryByText(/ocr|fault detected|identified as/i)).not.toBeInTheDocument();
  });
});
