import { registerDraft, approvedNavigation } from "@/lib/desktop-lifecycle";
import { onMounted, onUnmounted, type Ref } from "vue";
export function useUnsavedChanges(dirty: Readonly<Ref<boolean>>) {
  function beforeUnload(event: BeforeUnloadEvent) {
    if (!dirty.value || approvedNavigation) return;
    event.preventDefault();
    event.returnValue = "";
  }
  let unregister: (() => void) | undefined;
  onMounted(() => {
    unregister = registerDraft(dirty);
    window.addEventListener("beforeunload", beforeUnload);
  });
  onUnmounted(() => {
    unregister?.();
    window.removeEventListener("beforeunload", beforeUnload);
  });
}
