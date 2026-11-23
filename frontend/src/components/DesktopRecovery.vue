<script setup lang="ts">
import { onMounted, onUnmounted } from "vue";
import {
  backendStopped,
  recoveryHosts,
  requestDesktopAction,
} from "@/lib/desktop-lifecycle";
const props = defineProps<{ inline?: boolean }>();
onMounted(() => {
  if (props.inline) recoveryHosts.value++;
});
onUnmounted(() => {
  if (props.inline) recoveryHosts.value--;
});
</script>
<template>
  <div
    v-if="backendStopped && (inline || recoveryHosts === 0)"
    class="desktop-recovery"
    :class="{ 'desktop-recovery-inline': inline }"
    role="alert"
  >
    <span>本地服务已停止，当前修改暂时无法保存。</span>
    <button
      class="ui-button button-outline"
      @click="requestDesktopAction('restart')"
    >
      重启应用
    </button>
  </div>
</template>
