<script setup lang="ts">
import { confirmAction } from "@/lib/confirmation";
import Feedback from "@/components/Feedback.vue";
import { ref, watch, computed } from "vue";
import {
  DialogRoot,
  DialogPortal,
  DialogOverlay,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "reka-ui";
import { X, Trash2, ExternalLink } from "@lucide/vue";
import Button from "./ui/button/Button.vue";
import type { Paper } from "@/lib/types";
import { parseTags } from "@/lib/library";
import { useUnsavedChanges } from "@/composables/useUnsavedChanges";
import { api, pdfUrl } from "@/lib/api";
const props = defineProps<{
  paper: Paper | null;
  availableTags: string[];
  busy: boolean;
  error: string;
}>();
const emit = defineEmits<{
  close: [];
  save: [
    paper: Paper,
    fields: {
      title: string;
      tags: string[];
      notes: string;
      authors: string;
      year: string;
      venue: string;
      bib: string;
    },
  ];
  remove: [paper: Paper];
}>();
const authors = ref(""),
  year = ref(""),
  venue = ref(""),
  bib = ref(""),
  folderError = ref("");
async function openFolder() {
  try {
    if (props.paper) await api.openFolder(props.paper);
  } catch (e) {
    folderError.value = String(e);
  }
}
const title = ref(""),
  tags = ref(""),
  notes = ref("");
watch(
  () => props.paper,
  (paper) => {
    folderError.value = "";
    authors.value = paper?.authors || "";
    year.value = paper?.year || "";
    venue.value = paper?.venue || "";
    bib.value = paper?.bib || "";
    title.value = paper?.title || "";
    tags.value = paper?.tags.join(", ") || "";
    notes.value = paper?.notes || "";
  },
);
const dirty = computed(
  () =>
    !!props.paper &&
    (title.value !== props.paper.title ||
      authors.value !== props.paper.authors ||
      year.value !== props.paper.year ||
      venue.value !== props.paper.venue ||
      bib.value !== props.paper.bib ||
      notes.value !== props.paper.notes ||
      JSON.stringify(parseTags(tags.value)) !==
        JSON.stringify(props.paper.tags)),
);
useUnsavedChanges(dirty);
async function close() {
  if (
    !props.busy &&
    (!dirty.value || (await confirmAction("放弃未保存的论文修改？")))
  )
    emit("close");
}
const tagSuggestions = computed(() => {
  const parts = tags.value.split(/[,，]/),
    needle = (parts.pop() || "").trim().toLowerCase();
  const chosen = new Set(parts.map((p) => p.trim()));
  return props.availableTags
    .filter((tag) => !chosen.has(tag) && tag.toLowerCase().includes(needle))
    .slice(0, 8);
});
function addTag(tag: string) {
  const parts = tags.value.split(/[,，]/);
  parts.pop();
  tags.value =
    [...new Set([...parts.map((p) => p.trim()).filter(Boolean), tag])].join(
      ", ",
    ) + ", ";
}
function save() {
  if (props.paper && title.value.trim())
    emit("save", props.paper, {
      title: title.value.trim(),
      tags: parseTags(tags.value),
      notes: notes.value,
      authors: authors.value,
      year: year.value,
      venue: venue.value,
      bib: bib.value,
    });
}
</script>
<template>
  <DialogRoot
    :open="!!paper"
    @update:open="
      (open) => {
        if (!open) close();
      }
    "
  >
    <DialogPortal
      ><DialogOverlay class="dialog-overlay" /><DialogContent
        class="dialog-content"
        @escape-key-down="
          (event) => {
            event.preventDefault();
            close();
          }
        "
        @pointer-down-outside="(event) => event.preventDefault()"
      >
        <DialogTitle class="dialog-title">论文信息</DialogTitle
        ><DialogDescription class="sr-only"
          >编辑论文信息和笔记。</DialogDescription
        >
        <button
          class="dialog-close"
          aria-label="关闭"
          :disabled="busy"
          @click="close"
        >
          <X :size="19" />
        </button>
        <form @submit.prevent="save">
          <label
            >标题<input
              v-model="title"
              required
              maxlength="1000"
              :disabled="busy"
          /></label>
          <label>作者<input v-model="authors" :disabled="busy" /></label>
          <div class="settings-numbers">
            <label>年份<input v-model="year" :disabled="busy" /></label
            ><label
              >会议 / 期刊<input v-model="venue" :disabled="busy"
            /></label>
          </div>
          <label
            >BibTeX<textarea v-model="bib" rows="3" :disabled="busy" />
          </label>
          <label
            >标签<input
              v-model="tags"
              placeholder="用逗号分隔，如 OOD, 计算机视觉"
              :disabled="busy"
          /></label>
          <div class="tag-suggestions">
            <button
              v-for="tag in tagSuggestions"
              :key="tag"
              type="button"
              :disabled="busy"
              :aria-label="'添加标签 ' + tag"
              @click="addTag(tag)"
            >
              {{ tag }}
            </button>
          </div>
          <label
            >阅读笔记<textarea
              v-model="notes"
              rows="6"
              placeholder="记下问题、想法或下一步…"
              :disabled="busy"
            ></textarea>
          </label>
          <Feedback :message="error" />
          <p v-if="folderError" role="alert" class="inline-error">
            {{ folderError }}
          </p>
          <button type="button" @click="openFolder">打开所在目录</button>
          <div class="editor-links">
            <a
              v-if="paper && pdfUrl(paper)"
              :href="pdfUrl(paper)!"
              target="_blank"
              rel="noopener"
              ><ExternalLink :size="14" />打开原始 PDF</a
            ><button
              type="button"
              class="danger-link"
              :disabled="busy"
              @click="paper && emit('remove', paper)"
            >
              <Trash2 :size="14" />移入回收站
            </button>
          </div>
          <div class="dialog-footer">
            <Button
              type="button"
              variant="outline"
              :disabled="busy"
              @click="close"
              >取消</Button
            ><Button type="submit" :disabled="busy || !title.trim()">{{
              busy ? "保存中…" : "保存修改"
            }}</Button>
          </div>
        </form>
      </DialogContent></DialogPortal
    >
  </DialogRoot>
</template>
