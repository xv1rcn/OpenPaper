import { onUnmounted, watch, type Ref } from "vue";
/** Only ephemeral success messages; warnings and errors must remain visible. */
export function useTransientMessage(message: Ref<string>, duration = 4000) {
  let timer: ReturnType<typeof setTimeout> | undefined;
  watch(message, (value) => {
    clearTimeout(timer);
    if (value)
      timer = setTimeout(() => {
        message.value = "";
      }, duration);
  });
  onUnmounted(() => clearTimeout(timer));
}
