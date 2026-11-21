import { onMounted, onUnmounted, type Ref } from "vue";
export function useUnsavedChanges(dirty: Readonly<Ref<boolean>>) {
  function beforeUnload(event: BeforeUnloadEvent) {
    if (!dirty.value) return;
    event.preventDefault();
    event.returnValue = "";
  }
  onMounted(() => window.addEventListener("beforeunload", beforeUnload));
  onUnmounted(() => window.removeEventListener("beforeunload", beforeUnload));
}
