<script setup lang="ts">
import NoteText from "./NoteText.vue";
import { BookOpen, Check, MoreHorizontal, ArrowUpRight } from "@lucide/vue";
import type { Paper } from "@/lib/types";
import { readerUrl } from "@/lib/api";
defineProps<{ paper: Paper; layout: "grid" | "list"; busy: boolean }>();
defineEmits<{ edit: [paper: Paper]; toggleRead: [paper: Paper] }>();
</script>
<template>
  <article
    class="paper-card"
    :class="{ 'paper-row': layout === 'list', 'is-read': paper.read }"
  >
    <a
      :href="readerUrl(paper)"
      class="paper-cover"
      :aria-label="`阅读 ${paper.title}`"
    >
      <div class="cover-top">
        <span>{{ paper.venue }}</span><span>{{ paper.year }}</span>
      </div>
      <div class="cover-title">{{ paper.title }}</div>
      <div class="cover-lines" aria-hidden="true">
        <i></i><i></i><i></i><i></i><i></i>
      </div>
      <div class="cover-footer">
        <ArrowUpRight :size="15" />
      </div>
    </a>
    <div class="paper-info">
      <div class="paper-meta">
        <span>{{
          [paper.venue, paper.year].filter(Boolean).join(" · ")
        }}</span><span v-if="paper.read" class="read-badge"
          ><Check :size="11" /> 已读</span
        >
      </div>
      <a class="paper-title" :href="readerUrl(paper)">{{ paper.title }}</a>
      <p
        v-if="paper.authors && paper.authors !== 'Unknown'"
        class="paper-authors"
      >
        {{ paper.authors }}
      </p>
      <div class="paper-tags">
        <span v-for="tag in paper.tags.slice(0, 3)" :key="tag">{{
          tag
        }}</span><span v-if="paper.tags.length > 3"
          >+{{ paper.tags.length - 3 }}</span
        >
      </div>
      <details v-if="paper.notes" class="card-note">
        <summary>阅读笔记</summary>
        <p><NoteText :text="paper.notes" /></p>
      </details>
      <a class="speedread-link" :href="readerUrl(paper)">{{
        paper.speedread_status === "success"
          ? "查看速读"
          : paper.speedread_status === "running"
            ? "速读生成中…"
            : paper.speedread_status === "error"
              ? "速读失败 · 查看详情"
              : "生成速读"
      }}</a>
      <div class="card-actions">
        <button
          :disabled="busy"
          :aria-label="`${paper.read ? '标记未读' : '标记已读'}：${paper.title}`"
          @click="$emit('toggleRead', paper)"
        >
          <BookOpen :size="14" />{{
            paper.read ? "标记未读" : "标记已读"
          }}</button
        ><button
          :aria-label="`编辑：${paper.title}`"
          @click="$emit('edit', paper)"
        >
          <MoreHorizontal :size="19" />
        </button>
      </div>
    </div>
  </article>
</template>
