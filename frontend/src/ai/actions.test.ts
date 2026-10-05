import { describe, expect, it } from "vitest";
import { actionPath } from "./actions";
import type { ActionItem, ActionType } from "../api/types";

function action(type: ActionType): ActionItem {
  return { id: "x", label: "x", type };
}

describe("actionPath", () => {
  it("maps every allowed action type to a real in-app route", () => {
    expect(actionPath(action("WHAT_IF"))).toBe("/what-if");
    expect(actionPath(action("VIEW_DRIVE"))).toBe("/drive");
    expect(actionPath(action("VIEW_CONTRIBUTORS"))).toBe("/why-range");
    expect(actionPath(action("VIEW_RECOMMENDATIONS"))).toBe("/why-range");
    expect(actionPath(action("VIEW_COST"))).toBe("/cost");
    expect(actionPath(action("VIEW_BATTERY"))).toBe("/vehicle#battery-stress");
  });
});
