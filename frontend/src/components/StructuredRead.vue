<script setup lang="ts">
import { computed } from "vue";
import { hasReadingContent } from "@/lib/reading";
const props = defineProps<{ value: unknown; depth?: number; field?: string }>();
defineEmits<{ page: [value: number] }>();
const labels: Record<string, string> = {
  technical_explanation: "技术解释",
  paper_context: "本文语境",
  basis: "依据",
  description: "说明",
  result: "结果",
  task: "任务",
  notes: "说明",
  estimated_input_tokens: "预计输入 Token",
  estimated_image_tokens: "预计图片 Token",
  image_count: "图片数量",
  figure_count: "图表数量",
  max_output_tokens: "输出预算上限",
  requested_output_tokens: "请求输出上限",
  target_output_tokens: "目标输出上限",
  context_window: "模型上下文上限",
  model_max_output_tokens: "模型输出上限",
  effective_context_limit: "有效上下文上限",
  effective_output_limit: "有效输出上限",
  safety_tokens: "预留 Token",
  limits_source: "上限依据",
  limit_sources: "参考来源",
  budget_notes: "估算说明",
  target_fits: "预算充足",
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
const entries = computed(() =>
  props.value && typeof props.value === "object" && !Array.isArray(props.value)
    ? Object.entries(props.value).filter(([, item]) => hasReadingContent(item))
    : [],
);
const known = computed(() => entries.value.filter(([key]) => key in labels));
const extra = computed(() =>
  Object.fromEntries(entries.value.filter(([key]) => !(key in labels))),
);
const text = computed(() => {
  const enums: Record<string, Record<string, string>> = {
    basis: { paper: "论文原文", general_background: "背景知识" },
    reproduction_difficulty: {
      low: "低",
      medium: "中",
      high: "高",
      unknown: "未评估",
    },
    role: { baseline: "对照方法", proposed: "本文方法", ablation: "消融对照" },
  };
  if (typeof props.value === "boolean") return props.value ? "是" : "否";
  if (props.field === "limits_source")
    return String(props.value)
      .split("+")
      .map(
        (v) =>
          ({
            official: "服务商",
            manual: "手动设置",
            conservative_default: "保守估算",
          })[v] || "其他",
      )
      .join("、");
  return enums[props.field || ""]?.[String(props.value)] || props.value;
});
</script>
<template>
  <template v-if="!hasReadingContent(value)" />
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
    <template v-for="[key, item] in known" :key="key"
      ><dt>{{ labels[key] }}</dt>
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
          :field="key"
          :depth="(depth || 0) + 1"
          @page="$emit('page', $event)"
        /></dd
    ></template>
    <details v-if="Object.keys(extra).length" class="extra-reading-fields">
      <summary>其他结果字段</summary>
      <pre>{{ JSON.stringify(extra, null, 2) }}</pre>
    </details>
  </dl>
  <p v-else class="reading-text">{{ text }}</p>
</template>
