<script setup lang="ts">
import { backendStopped, requestDesktopAction } from "@/lib/desktop-lifecycle";
</script>
<template>
  <div v-if="backendStopped" class="desktop-recovery" role="alert">
    <span>本地服务已停止，当前修改暂时无法保存。</span>
    <button
      class="ui-button button-outline"
      @click="requestDesktopAction('restart')"
    >
      重启应用
    </button>
  </div>
</template>
