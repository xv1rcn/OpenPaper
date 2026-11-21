<script setup lang="ts">
import NoteText from "./NoteText.vue";
import { ref, computed, onMounted, onUnmounted } from "vue";
import { ArrowLeft, RefreshCw, Download, Settings2, Trash2 } from "@lucide/vue";
import Button from "./ui/button/Button.vue";
import SettingsPanel from "./SettingsPanel.vue";
import StructuredRead from "./StructuredRead.vue";
import { api, request, normalizePaper, pdfUrl } from "@/lib/api";
import {
  loadReading,
  normalizeReading,
  safeFigure,
  exportReading,
  type SpeedRead,
} from "@/lib/reading";
import type { Paper } from "@/lib/types";
const props = defineProps<{ fileKey: string }>();
const paper = ref<Paper | null>(null),
  reading = ref<SpeedRead>({}),
  error = ref(""),
  pending = ref(false),
  loading = ref(true),
  settings = ref(false),
  optionsOpen = ref(false),
  exportBusy = ref(false);
const page = ref(1),
  showPdf = ref(true),
  width = ref(50),
  depth = ref("standard"),
  extra = ref(""),
  figures = ref(true),
  maxFigures = ref(5);
const focus = ref(["general", "experiment", "reproduction", "figure"]);
const normalized = computed(() => normalizeReading(reading.value));
const sections = [
  ["one_sentence", "快速省流总结"],
  ["quick_takeaways", "核心要点"],
  ["problem_and_motivation", "问题与动机"],
  ["method_overview", "方法概述"],
  ["method_steps", "方法步骤"],
  ["technical_detail_read", "技术细节"],
  ["experiment_read", "实验解读"],
  ["contributions", "主要贡献"],
  ["limitations", "局限"],
  ["figure_insights", "图表解读"],
  ["deep_read_suggestions", "精读建议"],
];
const pdf = computed(() => paper.value && pdfUrl(paper.value));
const figureItems = computed(
  () =>
    (Array.isArray(normalized.value.figure_insights)
      ? normalized.value.figure_insights
      : []) as Record<string, unknown>[],
);
const storageKey = "openpaper-reader-" + props.fileKey;
function saveLayout() {
  try {
    localStorage.setItem(
      storageKey,
      JSON.stringify({
        page: page.value,
        width: width.value,
        showPdf: showPdf.value,
      }),
    );
  } catch {}
}
function jump(value: number) {
  if (Number.isInteger(value) && value > 0) {
    page.value = value;
    showPdf.value = true;
    saveLayout();
  }
}
let timer: ReturnType<typeof setInterval> | undefined,
  polling = false,
  active = true;
async function refresh() {
  if (polling) return;
  polling = true;
  try {
    const data = await loadReading(props.fileKey);
    if (active) reading.value = data.speed_read || {};
  } catch (e) {
    if (active) error.value = String(e);
  } finally {
    polling = false;
  }
}
async function generate() {
  if (pending.value || reading.value.status === "running") return;
  if (
    reading.value.status === "success" &&
    !confirm("重新生成将替换当前速读结果，并调用模型。继续吗？")
  )
    return;
  pending.value = true;
  error.value = "";
  optionsOpen.value = false;
  try {
    const data = await request<{ speed_read: SpeedRead }>(
      "/api/generate-speedread",
      {
        file_key: props.fileKey,
        force: true,
        apiConfig: { useSaved: true },
        options: {
          depth: depth.value,
          focus: focus.value,
          extra_prompt: extra.value,
          include_figure_insights: figures.value,
          max_figures: maxFigures.value,
        },
      },
    );
    if (active) reading.value = data.speed_read;
  } catch (e) {
    if (active) error.value = String(e);
  } finally {
    pending.value = false;
    if (active) await refresh();
  }
}
async function remove() {
  if (!confirm("将这篇论文的速读结果移入回收站？PDF 原文会保留。")) return;
  try {
    await api.deleteSpeedread(props.fileKey);
    reading.value = {};
  } catch (e) {
    error.value = String(e);
  }
}
async function exportAs(format: "pdf" | "pptx") {
  exportBusy.value = true;
  error.value = "";
  try {
    await exportReading(props.fileKey, format);
  } catch (e) {
    error.value = String(e);
  } finally {
    exportBusy.value = false;
  }
}
onMounted(async () => {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || "{}");
    if (Number.isInteger(saved.page) && saved.page > 0) page.value = saved.page;
    if (saved.width >= 25 && saved.width <= 70) width.value = saved.width;
    if (typeof saved.showPdf === "boolean") showPdf.value = saved.showPdf;
  } catch {}
  try {
    const data = await api.library();
    paper.value =
      data.papers
        .map(normalizePaper)
        .find((p) => p.file_key === props.fileKey) || null;
    if (!paper.value) throw new Error("论文不存在或已移入回收站");
    await refresh();
    const old = reading.value.options || {};
    if (["brief", "standard", "deep"].includes(String(old.depth)))
      depth.value = String(old.depth);
    if (Array.isArray(old.focus))
      focus.value = old.focus.filter(
        (v): v is string =>
          typeof v === "string" &&
          ["general", "experiment", "reproduction", "figure"].includes(v),
      );
    if (typeof old.include_figure_insights === "boolean")
      figures.value = old.include_figure_insights;
    if (typeof old.max_figures === "number") maxFigures.value = old.max_figures;
    if (typeof old.extra_prompt === "string") extra.value = old.extra_prompt;
  } catch (e) {
    error.value = String(e);
  } finally {
    loading.value = false;
  }
  timer = setInterval(() => {
    if (pending.value || reading.value.status === "running") refresh();
  }, 1500);
});
onUnmounted(() => {
  active = false;
  if (timer) clearInterval(timer);
});
</script>
<template>
  <div class="reader-workspace">
    <header class="reader-header">
      <a href="/app/" class="ui-button button-ghost"
        ><ArrowLeft :size="16" />书库</a
      >
      <h1>{{ paper?.title || "阅读工作区" }}</h1>
      <Button variant="ghost" @click="settings = true"
        ><Settings2 :size="16" />设置</Button
      >
    </header>
    <div v-if="loading" class="empty-state">正在加载论文与已有速读…</div>
    <template v-else
      ><div class="reader-toolbar">
        <label
          ><input
            v-model="showPdf"
            type="checkbox"
            @change="saveLayout"
          />原文对照</label
        ><label v-if="showPdf"
          >页码<input
            :value="page"
            type="number"
            min="1"
            aria-label="PDF 页码"
            @change="
              jump(Number(($event.target as HTMLInputElement).value))
            " /></label
        ><label v-if="showPdf" class="split-control"
          >原文宽度<input
            v-model.number="width"
            type="range"
            min="25"
            max="70"
            @change="saveLayout" /></label
        ><Button
          :disabled="pending || reading.status === 'running' || !paper"
          @click="optionsOpen = !optionsOpen"
          >{{
            pending || reading.status === "running"
              ? "生成中…"
              : reading.status === "success"
                ? "重新生成速读"
                : "生成速读"
          }}</Button
        ><Button
          variant="outline"
          :disabled="pending || exportBusy || reading.status !== 'success'"
          @click="exportAs('pdf')"
          ><Download :size="14" />PDF</Button
        ><Button
          variant="outline"
          :disabled="pending || exportBusy || reading.status !== 'success'"
          @click="exportAs('pptx')"
          >PPTX</Button
        ><Button variant="ghost" :disabled="pending" @click="refresh"
          ><RefreshCw :size="14" />刷新</Button
        ><Button
          variant="ghost"
          :disabled="pending || !reading.status"
          @click="remove"
          ><Trash2 :size="14" />删除速读</Button
        >
      </div>
      <section v-if="optionsOpen" class="generate-options">
        <h2>速读生成选项</h2>
        <label
          >深度<select v-model="depth">
            <option value="brief">简要</option>
            <option value="standard">标准</option>
            <option value="deep">深入</option>
          </select></label
        >
        <fieldset>
          <legend>关注方向</legend>
          <label
            v-for="(label, key) in {
              general: '整体理解',
              experiment: '实验',
              reproduction: '复现',
              figure: '图表',
            }"
            :key="key"
            ><input v-model="focus" type="checkbox" :value="key" />{{
              label
            }}</label
          >
        </fieldset>
        <label>补充要求<textarea v-model="extra" rows="2" /></label
        ><label><input v-model="figures" type="checkbox" />包含图表解读</label
        ><label
          >图表数量<input
            v-model.number="maxFigures"
            type="number"
            min="3"
            max="12" /></label
        ><Button :disabled="pending || !focus.length" @click="generate"
          >开始生成（会调用模型）</Button
        >
      </section>
      <p v-if="error" role="alert" class="error-banner">{{ error }}</p>
      <div
        v-if="pending || reading.status === 'running'"
        class="reader-progress"
        role="status"
      >
        {{ reading.progress?.message || "正在生成速读，可以继续阅读原文…"
        }}<progress :value="reading.progress?.percent || 0" max="100" />
      </div>
      <div class="reader-columns">
        <section
          v-if="showPdf && pdf"
          class="pdf-panel"
          :style="{ width: width + '%' }"
        >
          <iframe :src="pdf + '#page=' + page" title="PDF 原文" /><a
            :href="pdf"
            target="_blank"
            rel="noopener"
            >在独立窗口打开原始 PDF</a
          >
        </section>
        <article class="reading-content">
          <nav v-if="reading.status === 'success'" class="reading-toc">
            <a v-for="[key, label] in sections" :key="key" :href="'#' + key">{{
              label
            }}</a>
          </nav>
          <p v-if="reading.model" class="field-help">
            模型：{{ reading.model }} · {{ reading.updated_at }}
          </p>
          <div
            v-if="reading.status === 'error'"
            role="alert"
            class="error-banner"
          >
            {{ reading.error }}
          </div>
          <div v-if="!reading.content" class="empty-state">
            <h2>原文已就绪</h2>
            <p>生成速读后，这里会显示总结、方法、实验与图表解读。</p>
          </div>
          <template v-else
            ><section
              v-for="[key, label] in sections"
              :id="key"
              :key="key"
              class="reading-section"
            >
              <h2>{{ label }}</h2>
              <template v-if="key === 'figure_insights'"
                ><article
                  v-for="(figure, index) in figureItems"
                  :key="index"
                  class="reading-figure"
                >
                  <img
                    v-if="safeFigure(figure.image_path)"
                    :src="safeFigure(figure.image_path)"
                    :alt="String(figure.label || '论文图表')"
                    loading="lazy"
                  />
                  <h3>{{ figure.title || figure.label }}</h3>
                  <p>{{ figure.summary }}</p>
                  <button
                    class="page-reference"
                    @click="jump(Number(figure.page))"
                  >
                    查看第 {{ figure.page }} 页
                  </button>
                </article></template
              ><StructuredRead
                v-else
                :value="normalized[key]"
                @page="jump"
              /></section
          ></template>
          <details v-if="reading.token_status" class="token-details">
            <summary>Token 预算与用量</summary>
            <StructuredRead :value="reading.token_status" />
          </details>
          <section v-if="paper?.notes" class="reading-section">
            <h2>我的笔记</h2>
            <p class="reading-text"><NoteText :text="paper.notes" /></p>
          </section>
        </article></div
    ></template>
    <SettingsPanel v-if="settings" @close="settings = false" />
  </div>
</template>
