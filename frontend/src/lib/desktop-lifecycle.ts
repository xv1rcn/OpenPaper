import { ref, type Ref } from "vue";
import { confirmAction } from "./confirmation";

const drafts = new Set<Readonly<Ref<boolean>>>();
export const backendStopped = ref(false);
export const recoveryHosts = ref(0);
export let approvedNavigation = false;
let requesting = false;
let installed = false;
export function registerDraft(dirty: Readonly<Ref<boolean>>) {
  drafts.add(dirty);
  return () => {
    drafts.delete(dirty);
  };
}
export function hasUnsavedDrafts() {
  return [...drafts].some((dirty) => dirty.value);
}
export async function requestDesktopAction(
  action: "close" | "restart",
  navigate = (path: string) => window.location.assign(path),
) {
  if (requesting) return;
  requesting = true;
  try {
    if (
      hasUnsavedDrafts() &&
      !(await confirmAction(
        "有尚未保存的修改，继续将丢弃这些修改。",
        action === "close" ? "放弃修改并退出" : "放弃修改并重启",
      ))
    )
      return;
    approvedNavigation = true;
    navigate(`/desktop/${action}-approved`);
  } finally {
    requesting = false;
  }
}
export function installDesktopLifecycle() {
  if (
    installed ||
    !(window as Window & { __OPENPAPER_DESKTOP__?: boolean })
      .__OPENPAPER_DESKTOP__
  )
    return;
  installed = true;
  window.addEventListener("openpaper-close-request", () => {
    void requestDesktopAction("close");
  });
  window.addEventListener("openpaper-backend-stopped", () => {
    backendStopped.value = true;
  });
  window.location.assign("/desktop/ui-ready");
}
