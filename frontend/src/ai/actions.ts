// Maps a backend-supplied action to where it navigates. The frontend never
// invents an action -- every ActionItem comes straight from the AskResponse.
import type { ActionItem } from "../api/types";

export function actionPath(action: ActionItem): string {
  switch (action.type) {
    case "WHAT_IF":
      return "/what-if";
    case "VIEW_DRIVE":
      return "/drive";
    case "VIEW_CONTRIBUTORS":
      return "/why-range";
    case "VIEW_RECOMMENDATIONS":
      return "/why-range";
    case "VIEW_COST":
      return "/cost";
    case "VIEW_BATTERY":
      return "/vehicle#battery-stress";
  }
}
