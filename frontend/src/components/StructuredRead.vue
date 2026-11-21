<script setup lang="ts">
defineProps<{ value: unknown; depth?: number }>();
defineEmits<{ page: [value: number] }>();
const labels: Record<string, string> = {
  summary: "概述",
  modules: "方法模块",
  terms: "术语解释",
  background_notes: "背景知识",
  missing_details: "缺失细节",
  name: "名称",
  title: "标题",
  role: "作用",
  input: "输入",
  inputs: "输入",
  output: "输出",
  outputs: "输出",
  mechanism: "机制",
  purpose: "目的",
  steps: "步骤",
  details: "细节",
  explanation: "解释",
  term: "术语",
  definition: "定义",
  intuition: "直观理解",
  why_it_matters: "意义",
  page_refs: "原文页码",
  compared_methods: "对比方法",
  datasets: "数据集",
  metrics: "评价指标",
  main_results: "主要结果",
  reproduction_difficulty: "复现难度",
  reproduction_notes: "复现注意",
  workload_estimate: "工作量估计",
  evaluation_design_notes: "实验充分性",
  claim: "结论",
  evidence: "证据",
  meaning: "含义",
  why_used: "使用原因",
  limitation: "局限",
  setting: "设置",
  scale: "规模",
  split: "划分",
  source: "来源",
  fairness_notes: "公平性",
  category: "类别",
  strengths: "优势",
  weaknesses: "不足",
  implementation_notes: "实现说明",
};
</script>
<template>
  <p
    v-if="value === null || value === undefined || value === ''"
    class="field-help"
  >
    论文中未明确说明
  </p>
  <ul v-else-if="Array.isArray(value)" class="reading-list">
    <li v-for="(item, index) in value" :key="index">
      <StructuredRead
        :value="item"
        :depth="(depth || 0) + 1"
        @page="$emit('page', $event)"
      />
    </li>
  </ul>
  <dl
    v-else-if="typeof value === 'object' && (depth || 0) < 12"
    class="reading-record"
  >
    <template v-for="(item, key) in value" :key="key"
      ><dt>{{ labels[key] || key }}</dt>
      <dd>
        <template v-if="key === 'page_refs' && Array.isArray(item)"
          ><button
            v-for="page in item"
            :key="String(page)"
            class="page-reference"
            @click="$emit('page', Number(page))"
          >
            第 {{ page }} 页
          </button></template
        ><StructuredRead
          v-else
          :value="item"
          :depth="(depth || 0) + 1"
          @page="$emit('page', $event)"
        /></dd
    ></template>
  </dl>
  <p v-else class="reading-text">{{ value }}</p>
</template>
