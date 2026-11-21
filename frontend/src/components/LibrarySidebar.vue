<script setup lang="ts">
import {
  Library,
  BookOpen,
  CheckCheck,
  Hash,
  Trash2,
  Settings2,
  ChartColumn,
  SlidersHorizontal,
  Leaf,
} from "@lucide/vue";
import { ref } from "vue";
const tagQuery = ref("");
import type { Collection } from "@/lib/types";

defineProps<{
  collection: Collection;
  tag: string;
  tags: string[];
  total: number;
  unread: number;
  recycled: number;
}>();
defineEmits<{
  navigate: [collection: Collection, tag?: string];
  settings: [];
}>();
</script>
<template>
  <aside class="sidebar">
    <a class="brand" href="/app/"
      ><span class="brand-symbol"><Leaf :size="20" /></span>OpenPaper<span
        class="brand-dot"
        >.</span
      ></a
    >
    <div class="workspace-label">我的研究空间</div>
    <nav aria-label="论文集合">
      <button
        :class="{ active: collection === 'all' && !tag }"
        @click="$emit('navigate', 'all')"
      >
        <Library :size="18" />全部论文<span>{{ total }}</span>
      </button>
      <button
        :class="{ active: collection === 'unread' && !tag }"
        @click="$emit('navigate', 'unread')"
      >
        <BookOpen :size="18" />待读<span>{{ unread }}</span>
      </button>
      <button
        :class="{ active: collection === 'read' && !tag }"
        @click="$emit('navigate', 'read')"
      >
        <CheckCheck :size="18" />已读<span>{{ total - unread }}</span>
      </button>
    </nav>
    <nav class="secondary-navigation">
      <button
        :class="{ active: collection === 'stats' }"
        @click="$emit('navigate', 'stats')"
      >
        <ChartColumn :size="17" />统计面板</button
      ><button
        :class="{ active: collection === 'tools' }"
        @click="$emit('navigate', 'tools')"
      >
        <SlidersHorizontal :size="17" />导出与管理
      </button>
    </nav>
    <div class="workspace-label tag-heading">
      标签 <span>{{ tags.length }}</span>
    </div>
    <input
      class="tag-search"
      v-model="tagQuery"
      aria-label="查找标签"
      placeholder="查找标签…"
    />
    <nav class="tag-navigation" aria-label="标签筛选">
      <button
        v-for="item in tags.filter((t) =>
          t.toLowerCase().includes(tagQuery.toLowerCase()),
        )"
        :key="item"
        :class="{ active: tag === item }"
        @click="$emit('navigate', 'all', item)"
      >
        <Hash :size="16" /><span class="tag-name">{{ item }}</span>
      </button>
      <p v-if="!tags.length" class="sidebar-hint">
        在论文信息中添加标签，<br />让相关研究聚在一起。
      </p>
    </nav>
    <div class="sidebar-bottom">
      <nav>
        <button
          :class="{ active: collection === 'recycle' }"
          @click="$emit('navigate', 'recycle')"
        >
          <Trash2 :size="17" />回收站<span>{{ recycled }}</span></button
        ><button @click="$emit('settings')">
          <Settings2 :size="17" />速读设置
        </button>
      </nav>
      <div class="local-status"><span></span>本地论文库 · 无需账号</div>
    </div>
  </aside>
</template>
