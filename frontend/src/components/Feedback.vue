<script setup lang="ts">
import { computed } from "vue";
import { CircleCheck, CircleAlert, TriangleAlert } from "@lucide/vue";
const props = withDefaults(
  defineProps<{ message: string; kind?: "success" | "warning" | "error" }>(),
  { kind: "error" },
);
const clean = computed(() => props.message.replace(/^Error:\s*/, ""));
const technical = computed(() =>
  /\[Errno|Traceback|HTTP Error|fetch failed|Failed to fetch|Load failed|JSON|Unexpected token/i.test(
    clean.value,
  ),
);
const summary = computed(() => {
  if (!technical.value) return clean.value;
  if (/401|403/.test(clean.value))
    return "请求未获授权，请检查密钥或重新打开应用。";
  if (/429/.test(clean.value))
    return "请求过于频繁或额度不足，请稍后重试或检查服务商额度。";
  return "请求未完成，请检查连接后重试。";
});
</script>
<template>
  <div
    v-if="message"
    class="feedback"
    :class="`feedback-${kind}`"
    :role="kind === 'error' ? 'alert' : 'status'"
  >
    <CircleCheck v-if="kind === 'success'" :size="16" aria-hidden="true" />
    <TriangleAlert
      v-else-if="kind === 'warning'"
      :size="16"
      aria-hidden="true"
    />
    <CircleAlert v-else :size="16" aria-hidden="true" />
    <div>
      <span>{{ summary }}</span>
      <details v-if="technical">
        <summary>技术详情</summary>
        <p>{{ clean }}</p>
      </details>
      <slot />
    </div>
  </div>
</template>
