<script setup lang="ts">
import { viewState } from "@/lib/view-state";
import { computed, ref } from "vue";
import PaperCard from "./PaperCard.vue";
import type { Paper } from "@/lib/types";
const props = defineProps<{
  papers: Paper[];
  layout: "grid" | "list";
  busy: boolean;
}>();
defineEmits<{ edit: [paper: Paper]; toggleRead: [paper: Paper] }>();
const order = ref<string[]>([]),
  collapsed = ref<string[]>([]),
  dragged = ref<string | null>(null);
try {
  const raw = JSON.parse(
    viewState.getItem("openpaper-group-order") ||
      viewState.getItem("papers-visualizer-group-order-v1") ||
      "[]",
  );
  if (Array.isArray(raw))
    order.value = raw.filter((t) => typeof t === "string");
} catch {}
const groups = computed(() => {
  const tags = [
    ...new Set(props.papers.flatMap((p) => (p.tags.length ? p.tags : [""]))),
  ];
  tags.sort((a, b) => {
    const ai = order.value.indexOf(a),
      bi = order.value.indexOf(b);
    return (
      (ai < 0 ? 9999 : ai) - (bi < 0 ? 9999 : bi) || a.localeCompare(b, "zh-CN")
    );
  });
  return tags.map((tag) => ({
    tag,
    papers: props.papers.filter((p) =>
      tag ? p.tags.includes(tag) : !p.tags.length,
    ),
  }));
});
function persist() {
  try {
    viewState.setItem("openpaper-group-order", JSON.stringify(order.value));
  } catch {}
}
function move(tag: string, direction: number) {
  const next = groups.value.map((g) => g.tag),
    i = next.indexOf(tag),
    j = i + direction;
  if (j < 0 || j >= next.length) return;
  [next[i], next[j]] = [next[j], next[i]];
  order.value = next;
  persist();
}
function drop(tag: string) {
  if (dragged.value === null || dragged.value === tag) return;
  const next = groups.value
    .map((g) => g.tag)
    .filter((g) => g !== dragged.value);
  next.splice(next.indexOf(tag), 0, dragged.value);
  order.value = next;
  dragged.value = null;
  persist();
}
function toggle(tag: string) {
  collapsed.value = collapsed.value.includes(tag)
    ? collapsed.value.filter((t) => t !== tag)
    : [...collapsed.value, tag];
}
</script>
<template>
  <section class="grouped-library">
    <div class="tools-row">
      <button @click="collapsed = []">展开全部分组</button
      ><button @click="collapsed = groups.map((g) => g.tag)">
        折叠全部分组</button
      ><span class="field-help"
        >可拖动分组标题调整顺序；多标签论文会显示在各自分组。</span
      >
    </div>
    <section
      v-for="(group, index) in groups"
      :key="group.tag"
      class="paper-group"
    >
      <header
        draggable="true"
        @dragstart="dragged = group.tag"
        @dragend="dragged = null"
        @dragover.prevent
        @drop.prevent="drop(group.tag)"
      >
        <button
          :aria-expanded="!collapsed.includes(group.tag)"
          @click="toggle(group.tag)"
        >
          {{ collapsed.includes(group.tag) ? "▸" : "▾" }}
          {{ group.tag || "未分类" }} <small>{{ group.papers.length }}</small>
        </button>
        <div>
          <button
            :disabled="index === 0"
            :aria-label="'上移分组 ' + group.tag"
            @click="move(group.tag, -1)"
          >
            ↑</button
          ><button
            :disabled="index === groups.length - 1"
            :aria-label="'下移分组 ' + group.tag"
            @click="move(group.tag, 1)"
          >
            ↓
          </button>
        </div>
      </header>
      <div
        v-if="!collapsed.includes(group.tag)"
        class="paper-grid"
        :class="{ 'paper-list': layout === 'list' }"
      >
        <PaperCard
          v-for="paper in group.papers"
          :key="paper.file_key"
          :paper="paper"
          :layout="layout"
          :busy="busy"
          @edit="$emit('edit', $event)"
          @toggle-read="$emit('toggleRead', $event)"
        />
      </div>
    </section>
  </section>
</template>
