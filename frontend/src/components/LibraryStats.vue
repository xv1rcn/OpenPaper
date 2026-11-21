<script setup lang="ts">
import { computed } from "vue";
import type { Paper } from "@/lib/types";
const props = defineProps<{ papers: Paper[] }>();
function distribution(field: "venue" | "year" | "tags" | "added_at") {
  const result: Record<string, number> = {};
  for (const paper of props.papers) {
    const values =
      field === "tags"
        ? paper.tags
        : field === "added_at"
          ? [paper.added_at.slice(0, 7) || "未知"]
          : [paper[field] || "未知"];
    for (const value of values) result[value] = (result[value] || 0) + 1;
  }
  return Object.entries(result).sort((a, b) =>
    field === "year" || field === "added_at"
      ? a[0].localeCompare(b[0])
      : b[1] - a[1],
  );
}
const sections = computed(() => [
  { title: "会议与期刊", rows: distribution("venue") },
  { title: "发表年份", rows: distribution("year") },
  { title: "研究标签", rows: distribution("tags") },
  { title: "按月加入", rows: distribution("added_at") },
]);
const read = computed(() => props.papers.filter((p) => p.read).length);
</script>
<template>
  <section class="statistics-panel">
    <div class="stat-totals">
      <article>
        <strong>{{ papers.length }}</strong><span>全部论文</span>
      </article>
      <article>
        <strong>{{ read }}</strong><span>已读</span>
      </article>
      <article>
        <strong>{{ papers.length - read }}</strong><span>待读</span>
      </article>
      <article>
        <strong
          >{{
            papers.length ? Math.round((read / papers.length) * 100) : 0
          }}%</strong
        ><span>阅读完成率</span>
      </article>
    </div>
    <div class="stats-grid">
      <section v-for="section in sections" :key="section.title">
        <h2>{{ section.title }}</h2>
        <p v-if="!section.rows.length">暂无数据</p>
        <div
          v-for="[label, count] in section.rows"
          :key="label"
          class="stat-bar"
        >
          <span>{{ label }}</span><meter
            min="0"
            :max="Math.max(...section.rows.map((row) => row[1]), 1)"
            :value="count"
            :aria-label="label + ' ' + count + ' 篇'"
          /><b>{{ count }}</b>
        </div>
      </section>
    </div>
  </section>
</template>
