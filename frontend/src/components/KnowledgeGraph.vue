<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { Paper } from "@/lib/types";
import { readerUrl } from "@/lib/api";
const props = defineProps<{ papers: Paper[] }>();
const groupBy = ref("tag"),
  onlyRead = ref(false),
  hidePapers = ref(false),
  selected = ref("");
const zoom = ref(1),
  pan = ref({ x: 0, y: 0 });
let drag: { x: number; y: number; px: number; py: number } | null = null;
const papers = computed(() =>
  props.papers.filter((p) => !onlyRead.value || p.read),
);
function keys(p: Paper) {
  return groupBy.value === "tag"
    ? p.tags.length
      ? [...new Set(p.tags)]
      : ["未分类"]
    : [groupBy.value === "year" ? p.year || "未知" : p.venue || "未知"];
}
const groups = computed(() =>
  [...new Set(papers.value.flatMap(keys))].sort().map((name, i, all) => ({
    name,
    x: 400 + Math.cos((i * 2 * Math.PI) / all.length) * 270,
    y: 260 + Math.sin((i * 2 * Math.PI) / all.length) * 190,
  })),
);
const nodes = computed(() =>
  papers.value.map((paper, i, all) => ({
    paper,
    x: 400 + Math.cos(i * 2.39996) * 160 * Math.sqrt((i + 1) / all.length),
    y: 260 + Math.sin(i * 2.39996) * 130 * Math.sqrt((i + 1) / all.length),
    groups: groups.value.filter((g) => keys(paper).includes(g.name)),
  })),
);
const relations = computed(() => {
  const counts = new Map<
    string,
    {
      a: (typeof groups.value)[number];
      b: (typeof groups.value)[number];
      count: number;
    }
  >();
  for (const node of nodes.value)
    for (let i = 0; i < node.groups.length; i++)
      for (let j = i + 1; j < node.groups.length; j++) {
        const a = node.groups[i],
          b = node.groups[j],
          key = JSON.stringify([a.name, b.name]);
        const relation = counts.get(key) || { a, b, count: 0 };
        relation.count++;
        counts.set(key, relation);
      }
  return [...counts.values()];
});
const selectedPapers = computed(() =>
  papers.value.filter((p) => keys(p).includes(selected.value)),
);
function reset() {
  zoom.value = 1;
  pan.value = { x: 0, y: 0 };
}
function start(e: PointerEvent) {
  if ((e.target as Element).closest("a, [role=button]")) return;
  (e.currentTarget as Element).setPointerCapture(e.pointerId);
  drag = { x: e.clientX, y: e.clientY, px: pan.value.x, py: pan.value.y };
}
function move(e: PointerEvent) {
  if (!drag) return;
  const bounds = (e.currentTarget as Element).getBoundingClientRect();
  pan.value = {
    x: drag.px + ((e.clientX - drag.x) * 800) / bounds.width,
    y: drag.py + ((e.clientY - drag.y) * 520) / bounds.height,
  };
}
watch(groupBy, () => {
  selected.value = "";
  reset();
});
</script>
<template>
  <section class="knowledge-graph">
    <h2>论文关系</h2>
    <div class="tools-row">
      <label
        >分组依据<select v-model="groupBy">
          <option value="tag">标签</option>
          <option value="venue">会议/期刊</option>
          <option value="year">发表年份</option>
        </select></label
      ><label><input type="checkbox" v-model="onlyRead" />仅显示已读</label
      ><label><input type="checkbox" v-model="hidePapers" />隐藏论文节点</label
      ><label
        >缩放<input
          type="range"
          min="0.5"
          max="3"
          step="0.1"
          v-model.number="zoom" /></label
      ><button @click="reset">重置视图</button>
    </div>
    <p v-if="!papers.length">暂无论文</p>
    <svg
      v-else
      viewBox="0 0 800 520"
      class="relationship-graph"
      aria-label="论文与分类关系，可拖动视图，选择分类查看论文"
      @pointerdown="start"
      @pointermove="move"
      @pointerup="drag = null"
      @pointercancel="drag = null"
      @wheel.prevent="
        zoom = Math.max(0.5, Math.min(3, zoom - $event.deltaY * 0.001))
      "
    >
      <g
        :transform="`translate(${400 + pan.x} ${260 + pan.y}) scale(${zoom}) translate(-400 -260)`"
      >
        <template v-if="hidePapers">
          <line
            v-for="edge in relations"
            :key="edge.a.name + '\0' + edge.b.name"
            :x1="edge.a.x"
            :y1="edge.a.y"
            :x2="edge.b.x"
            :y2="edge.b.y"
            stroke="var(--accent)"
            :stroke-width="Math.min(8, edge.count)"
            opacity=".4"
          >
            <title>
              {{ edge.a.name }} ↔ {{ edge.b.name }}：{{ edge.count }} 篇
            </title>
          </line>
        </template>
        <template v-else>
          <g v-for="node in nodes" :key="node.paper.file_key">
            <line
              v-for="group in node.groups"
              :key="group.name"
              :x1="node.x"
              :y1="node.y"
              :x2="group.x"
              :y2="group.y"
              stroke="var(--accent)"
              opacity=".18"
            />
            <a
              :href="readerUrl(node.paper)"
              :aria-label="'阅读 ' + node.paper.title"
            >
              <circle
                :cx="node.x"
                :cy="node.y"
                r="5"
                :fill="node.paper.read ? 'var(--accent)' : 'currentColor'"
              >
                <title>{{ node.paper.title }}</title>
              </circle>
            </a>
          </g>
        </template>
        <g
          v-for="group in groups"
          :key="group.name"
          tabindex="0"
          role="button"
          :aria-label="'查看分类 ' + group.name"
          @click="selected = group.name"
          @keydown.enter="selected = group.name"
          @keydown.space.prevent="selected = group.name"
        >
          <circle :cx="group.x" :cy="group.y" r="12" fill="var(--accent)" />
          <text :x="group.x" :y="group.y - 20" text-anchor="middle">
            {{ group.name }}
          </text>
        </g>
      </g>
    </svg>
    <div v-if="selected">
      <h3>{{ selected }} · {{ selectedPapers.length }} 篇</h3>
      <ul>
        <li v-for="paper in selectedPapers" :key="paper.file_key">
          <a :href="readerUrl(paper)">{{ paper.title }}</a>
        </li>
      </ul>
    </div>
  </section>
</template>
