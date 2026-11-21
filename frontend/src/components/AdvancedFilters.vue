<script setup lang="ts">
import { ref, computed } from "vue";
import type { Paper } from "@/lib/types";
const props = defineProps<{ papers: Paper[]; allTags: string[] }>();
const search = ref("");
const matchingTags = computed(() =>
  props.allTags.filter((tag) =>
    tag.toLowerCase().includes(search.value.toLowerCase()),
  ),
);
const venue = defineModel<string>("venue", { required: true }),
  selected = defineModel<string[]>("tags", { required: true }),
  mode = defineModel<"any" | "all">("mode", { required: true });
</script>
<template>
  <details class="advanced-filters">
    <summary>
      更多筛选 <span v-if="venue || selected.length">· 已应用</span>
    </summary>
    <div class="tools-row">
      <label
        >会议 / 期刊<select v-model="venue" aria-label="会议期刊筛选">
          <option value="">全部会议 / 期刊</option>
          <option
            v-for="item in [
              ...new Set(papers.map((p) => p.venue).filter(Boolean)),
            ].sort()"
            :key="item"
          >
            {{ item }}
          </option>
        </select></label
      ><label
        >标签匹配<select v-model="mode">
          <option value="any">任一标签（OR）</option>
          <option value="all">全部标签（AND）</option>
        </select></label
      ><button @click="selected = [...allTags]">全选标签</button
      ><button
        @click="
          selected = [];
          venue = '';
        "
      >
        清空筛选</button
      ><button
        @click="selected = allTags.filter((tag) => !selected.includes(tag))"
      >
        反选标签
      </button>
    </div>
    <input v-model="search" aria-label="搜索筛选标签" placeholder="搜索标签" />
    <div class="filter-tags">
      <label v-for="tag in matchingTags" :key="tag"
        ><input v-model="selected" type="checkbox" :value="tag" />{{
          tag
        }}</label
      >
    </div>
  </details>
</template>
