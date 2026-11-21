<script setup lang="ts">
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
        <span>{{ paper.venue || "PAPER" }}</span><span>{{
          paper.year || "—"
        }}</span>
      </div>
      <div class="cover-title">{{ paper.title }}</div>
      <div class="cover-lines" aria-hidden="true">
        <i></i><i></i><i></i><i></i><i></i>
      </div>
      <div class="cover-footer">
        <span>RESEARCH PAPER</span><ArrowUpRight :size="15" />
      </div>
    </a>
    <div class="paper-info">
      <div class="paper-meta">
        <span>{{
          [paper.venue, paper.year].filter(Boolean).join(" · ") || "学术论文"
        }}</span><span v-if="paper.read" class="read-badge"
          ><Check :size="11" /> 已读</span
        >
      </div>
      <a class="paper-title" :href="readerUrl(paper)">{{ paper.title }}</a>
      <p class="paper-authors">
        {{
          paper.authors && paper.authors !== "Unknown"
            ? paper.authors
            : "作者信息待补充"
        }}
      </p>
      <div class="paper-tags">
        <span v-for="tag in paper.tags.slice(0, 3)" :key="tag">{{
          tag
        }}</span><span v-if="paper.tags.length > 3"
          >+{{ paper.tags.length - 3 }}</span
        >
      </div>
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
