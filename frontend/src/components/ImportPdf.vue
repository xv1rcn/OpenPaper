<script setup lang="ts">
import { ref } from "vue";
import { Plus, FileUp, X } from "@lucide/vue";
import Button from "./ui/button/Button.vue";
const props = defineProps<{ disabled: boolean }>();
const emit = defineEmits<{ complete: []; busy: [value: boolean] }>();
const input = ref<HTMLInputElement | null>(null),
  uploading = ref(false),
  results = ref<{ name: string; ok: boolean; message: string }[]>([]),
  current = ref("");
async function upload(event: Event) {
  const files = [...((event.target as HTMLInputElement).files || [])];
  if (!files.length || uploading.value || props.disabled) return;
  uploading.value = true;
  emit("busy", true);
  results.value = [];
  try {
    for (const file of files) {
      current.value = file.name;
      try {
        if (
          !file.name.toLowerCase().endsWith(".pdf") ||
          file.size === 0 ||
          file.size > 50 * 1024 * 1024
        )
          throw new Error("请选择不超过 50 MB 的非空 PDF");
        const response = await fetch("/api/import-pdf", {
          method: "POST",
          headers: {
            "Content-Type": "application/pdf",
            "X-OpenPaper-Request": "1",
            "X-File-Name": encodeURIComponent(file.name),
          },
          body: file,
        });
        const data = await response.json();
        if (!response.ok || !data.ok) throw new Error(data.error || "导入失败");
        results.value.push({
          name: file.name,
          ok: true,
          message:
            data.warning || (data.duplicate ? "已存在，未重复导入" : "已导入"),
        });
      } catch (e) {
        results.value.push({
          name: file.name,
          ok: false,
          message:
            e instanceof Error ? e.message : "上传失败；请刷新确认后重试",
        });
      }
    }
  } finally {
    uploading.value = false;
    current.value = "";
    emit("busy", false);
    emit("complete");
    if (input.value) input.value.value = "";
  }
}
</script>
<template>
  <div class="import-control">
    <input
      ref="input"
      class="file-input"
      type="file"
      accept=".pdf,application/pdf"
      multiple
      aria-label="选择 PDF 文件"
      :disabled="disabled || uploading"
      @change="upload"
    />
    <Button :disabled="disabled || uploading" @click="input?.click()"
      ><FileUp v-if="uploading" :size="16" /><Plus v-else :size="16" />{{
        uploading ? "正在导入…" : "导入 PDF"
      }}</Button
    >
    <section
      v-if="results.length || uploading"
      class="import-results"
      aria-label="导入结果"
      aria-live="polite"
    >
      <header>
        <strong>导入结果</strong
        ><button
          v-if="!uploading"
          aria-label="关闭导入结果"
          @click="results = []"
        >
          <X :size="15" />
        </button>
      </header>
      <p v-if="uploading">正在复制：{{ current }}</p>
      <p
        v-for="(result, index) in results"
        :key="index"
        :class="{ 'import-error': !result.ok }"
      >
        <span>{{ result.name }}</span><small>{{ result.message }}</small>
      </p>
      <footer>原文件保持不变 · 单个 PDF 最大 50 MB</footer>
    </section>
  </div>
</template>
