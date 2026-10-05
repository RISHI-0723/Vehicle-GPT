// Real Web Share API when present (phone-to-phone/phone-to-app sharing);
// falls back to the clipboard when it isn't. No fake share sheet.
import { writeToClipboard } from "./clipboard";

export type ShareOutcome = "shared" | "cancelled" | "copied" | "unavailable";

export async function shareText(title: string, text: string): Promise<ShareOutcome> {
  const nav = navigator as Navigator & { share?: (data: ShareData) => Promise<void> };
  if (nav.share) {
    try {
      await nav.share({ title, text });
      return "shared";
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        return "cancelled";
      }
      // fall through to clipboard for any other share failure
    }
  }
  const copied = await writeToClipboard(text);
  return copied ? "copied" : "unavailable";
}
