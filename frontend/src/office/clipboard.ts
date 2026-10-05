// Real clipboard access only. If the Clipboard API is unavailable or the
// write is rejected, callers get a plain false -- never a fake success.
export async function writeToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // fall through to report failure below
  }
  return false;
}
