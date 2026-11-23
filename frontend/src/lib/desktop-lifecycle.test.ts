import { describe, it, expect, vi } from "vitest";
import { ref } from "vue";
import {
  registerDraft,
  hasUnsavedDrafts,
  requestDesktopAction,
} from "./desktop-lifecycle";
import { finishConfirmation, confirmation } from "./confirmation";

describe("desktop exit and recovery", () => {
  it("cancels native close without discarding a draft and allows confirmed exit", async () => {
    const dirty = ref(true),
      unregister = registerDraft(dirty),
      navigate = vi.fn();
    const pending = requestDesktopAction("close", navigate);
    expect(confirmation.value?.action).toBe("放弃修改并退出");
    await requestDesktopAction("close", navigate);
    finishConfirmation(false);
    await pending;
    expect(navigate).not.toHaveBeenCalled();
    expect(hasUnsavedDrafts()).toBe(true);
    const accepted = requestDesktopAction("close", navigate);
    finishConfirmation(true);
    await accepted;
    expect(navigate).toHaveBeenCalledWith("/desktop/close-approved");
    unregister();
    expect(hasUnsavedDrafts()).toBe(false);
  });
  it("checks all registered drafts before restart and skips confirmation when clean", async () => {
    const first = ref(false),
      second = ref(true),
      a = registerDraft(first),
      b = registerDraft(second),
      navigate = vi.fn();
    const pending = requestDesktopAction("restart", navigate);
    expect(confirmation.value?.action).toBe("放弃修改并重启");
    finishConfirmation(false);
    await pending;
    expect(navigate).not.toHaveBeenCalled();
    second.value = false;
    await requestDesktopAction("restart", navigate);
    expect(navigate).toHaveBeenCalledWith("/desktop/restart-approved");
    a();
    b();
  });
});
