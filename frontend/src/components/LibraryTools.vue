<script setup lang="ts">
import { useTransientMessage } from "@/composables/useTransientMessage";
import { confirmAction } from "@/lib/confirmation";
import Feedback from "@/components/Feedback.vue";
import { ref, computed, nextTick } from "vue";
import Button from "./ui/button/Button.vue";
import { api, request } from "@/lib/api";
import { download, loadReading, normalizeReading } from "@/lib/reading";
import type { Paper } from "@/lib/types";
const props = defineProps<{
  papers: Paper[];
  filtered: Paper[];
  tags: string[];
}>();
const emit = defineEmits<{ changed: [] }>();
const logView = ref<HTMLElement | null>(null),
  autoScroll = ref(true);
const filteredLogs = computed(() =>
  logs.value
    .filter((line) =>
      line.toLowerCase().includes(logSearch.value.toLowerCase()),
    )
    .join("\n"),
);
async function copyLogs() {
  await run(async () => {
    await navigator.clipboard.writeText(filteredLogs.value);
    message.value = "日志已复制";
  });
}
const includeSummary = ref(false),
  busy = ref(false),
  error = ref(""),
  message = ref(""),
  logs = ref<string[]>([]),
  logSearch = ref("");
useTransientMessage(message);
async function run(action: () => Promise<void>) {
  busy.value = true;
  error.value = "";
  message.value = "";
  try {
    await action();
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    busy.value = false;
  }
}
async function markdown() {
  await run(async () => {
    const parts = ["# OpenPaper 论文导出", ""];
    for (const p of props.filtered) {
      parts.push(
        `## ${p.title}`,
        `${p.authors} · ${p.venue} · ${p.year}`,
        `标签：${p.tags.join(", ")}`,
        `状态：${p.read ? "已读" : "待读"}`,
        `PDF：${p.pdf}`,
        "",
        p.notes,
        "",
      );
      if (p.bib) parts.push("```bibtex", p.bib, "```", "");
      if (includeSummary.value) {
        const { speed_read } = await loadReading(p.file_key);
        if (speed_read?.status === "success") {
          const data = normalizeReading(speed_read);
          parts.push(
            "### 速读概要",
            String(data.one_sentence),
            "",
            ...(Array.isArray(data.quick_takeaways)
              ? data.quick_takeaways.map((v) => "- " + String(v))
              : []),
            "",
          );
        }
      }
    }
    download(
      new Blob([parts.join("\n")], { type: "text/markdown;charset=utf-8" }),
      "OpenPaper-library.md",
    );
    message.value = `已导出 ${props.filtered.length} 篇论文。`;
  });
}
async function metadata() {
  await run(async () => {
    const response = await fetch("/papers/metadata.json", {
      cache: "no-store",
    });
    if (!response.ok) throw new Error("无法读取元数据");
    download(
      new Blob([await response.text()], { type: "application/json" }),
      "metadata.json",
    );
  });
}
async function removeTag(tag: string) {
  if (
    await confirmAction(
      `删除标签“${tag}”？论文不会删除，可从回收站恢复标签。`,
      "删除标签",
    )
  )
    run(async () => {
      await api.deleteTag(tag);
      emit("changed");
      message.value = "标签已移入回收站。";
    });
}
function refreshLogs() {
  run(async () => {
    const data = await request<{ lines: string[] }>("/api/log?tail=500");
    logs.value = data.lines;
    await nextTick();
    if (autoScroll.value && logView.value)
      logView.value.scrollTop = logView.value.scrollHeight;
  });
}
</script>
<template>
  <section class="library-tools">
    <div class="tools-row">
      <label
        ><input v-model="includeSummary" type="checkbox" />Markdown
        包含已生成的速读概要</label
      ><Button :disabled="busy" @click="markdown"
        >导出 Markdown（{{ filtered.length }} 篇）</Button
      ><Button variant="outline" :disabled="busy" @click="metadata"
        >导出全库 JSON（{{ papers.length }} 篇）</Button
      >
    </div>
    <Feedback :message="error" />
    <Feedback :message="message" kind="success" />
    <h3>标签管理</h3>
    <div class="tag-management">
      <div v-for="tag in tags" :key="tag">
        <span># {{ tag }}</span
        ><button
          :disabled="busy"
          :aria-label="'删除标签 ' + tag"
          @click="removeTag(tag)"
        >
          删除标签
        </button>
      </div>
    </div>
    <details>
      <summary>运行日志</summary>
      <div class="tools-row">
        <Button variant="outline" :disabled="busy" @click="refreshLogs"
          >刷新日志</Button
        ><Button
          variant="outline"
          :disabled="busy || !filteredLogs"
          @click="copyLogs"
          >复制日志</Button
        >
        <label
          ><input type="checkbox" v-model="autoScroll" />自动滚动到底部</label
        ><input
          v-model="logSearch"
          aria-label="筛选日志"
          placeholder="筛选日志…"
        />
      </div>
      <pre ref="logView" class="log-content">{{
        filteredLogs || "暂无日志"
      }}</pre>
    </details>
  </section>
</template>
