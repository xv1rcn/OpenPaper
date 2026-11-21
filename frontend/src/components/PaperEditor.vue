<script setup lang="ts">
import { ref, watch } from "vue";
import {
  DialogRoot,
  DialogPortal,
  DialogOverlay,
  DialogContent,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from "reka-ui";
import { X, Trash2, ExternalLink } from "@lucide/vue";
import Button from "./ui/button/Button.vue";
import type { Paper } from "@/lib/types";
import { parseTags } from "@/lib/library";
import { pdfUrl } from "@/lib/api";
const props = defineProps<{
  paper: Paper | null;
  busy: boolean;
  error: string;
}>();
const emit = defineEmits<{
  close: [];
  save: [
    paper: Paper,
    fields: { title: string; tags: string[]; notes: string },
  ];
  remove: [paper: Paper];
}>();
const title = ref(""),
  tags = ref(""),
  notes = ref("");
watch(
  () => props.paper,
  (paper) => {
    title.value = paper?.title || "";
    tags.value = paper?.tags.join(", ") || "";
    notes.value = paper?.notes || "";
  },
);
function save() {
  if (props.paper && title.value.trim())
    emit("save", props.paper, {
      title: title.value.trim(),
      tags: parseTags(tags.value),
      notes: notes.value,
    });
}
</script>
<template>
  <DialogRoot
    :open="!!paper"
    @update:open="
      (open) => {
        if (!open && !busy) emit('close');
      }
    "
  >
    <DialogPortal
      ><DialogOverlay class="dialog-overlay" /><DialogContent
        class="dialog-content"
        @escape-key-down="
          (event) => {
            if (busy) event.preventDefault();
          }
        "
        @pointer-down-outside="(event) => event.preventDefault()"
      >
        <DialogTitle class="dialog-title">论文信息</DialogTitle
        ><DialogDescription class="dialog-description"
          >整理标题、标签和笔记。修改会保存在本地论文库。</DialogDescription
        >
        <DialogClose class="dialog-close" aria-label="关闭" :disabled="busy"
          ><X :size="19"
        /></DialogClose>
        <form @submit.prevent="save">
          <label
            >标题<input
              v-model="title"
              required
              maxlength="1000"
              :disabled="busy"
          /></label>
          <label
            >标签<input
              v-model="tags"
              placeholder="用逗号分隔，如 OOD, 计算机视觉"
              :disabled="busy"
          /></label>
          <label
            >阅读笔记<textarea
              v-model="notes"
              rows="6"
              placeholder="记下问题、想法或下一步…"
              :disabled="busy"
            ></textarea>
          </label>
          <p v-if="error" class="inline-error" role="alert">{{ error }}</p>
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
              @click="emit('close')"
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
