<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import Button from "./ui/button/Button.vue";
import {
  preferencesApi,
  appearanceDefaults,
  applyAppearance,
} from "@/lib/preferences";
const emit = defineEmits<{ busy: [value: boolean]; dirty: [value: boolean] }>();
const baseline = ref(JSON.stringify(appearanceDefaults));
const values = ref({ ...appearanceDefaults }),
  revision = ref<string | null>(null),
  busy = ref(false),
  message = ref(""),
  error = ref("");
const dirty = computed(() => JSON.stringify(values.value) !== baseline.value);
watch(busy, (value) => emit("busy", value));
watch(dirty, (value) => emit("dirty", value));
async function load() {
  if (dirty.value && !confirm("放弃未保存的外观修改？")) return;
  busy.value = true;
  try {
    const data = await preferencesApi.load();
    values.value = data.values;
    baseline.value = JSON.stringify(data.values);
    revision.value = data.revision;
    error.value = "";
  } catch (e) {
    error.value = String(e);
  } finally {
    busy.value = false;
  }
}
async function save() {
  if (revision.value === null) return;
  busy.value = true;
  error.value = "";
  try {
    const data = await preferencesApi.save(values.value, revision.value);
    revision.value = data.revision;
    baseline.value = JSON.stringify(data.values);
    applyAppearance(data.values);
    message.value = "已保存";
  } catch (e) {
    error.value = String(e);
  } finally {
    busy.value = false;
  }
}
function preset(theme: string) {
  values.value =
    theme === "dark"
      ? {
          theme: "dark",
          accent: "#8eaf93",
          background: "#1d2520",
          readBackground: "#2c3c30",
        }
      : theme === "paper"
        ? {
            theme: "light",
            accent: "#8b6846",
            background: "#f6f1e6",
            readBackground: "#efe5d0",
          }
        : { ...appearanceDefaults };
}
onMounted(load);
</script>
<template>
  <section class="appearance-settings">
    <h3>外观</h3>
    <div class="preset-buttons">
      <Button variant="outline" :disabled="busy" @click="preset('light')"
        >浅色</Button
      ><Button variant="outline" :disabled="busy" @click="preset('paper')"
        >暖纸</Button
      ><Button variant="outline" :disabled="busy" @click="preset('dark')"
        >深色</Button
      >
    </div>
    <label
      >主题色<input
        v-model="values.accent"
        type="color"
        :disabled="busy" /></label
    ><label
      >页面背景<input
        v-model="values.background"
        type="color"
        :disabled="busy" /></label
    ><label
      >已读卡片背景<input
        v-model="values.readBackground"
        type="color"
        :disabled="busy"
    /></label>
    <p v-if="error" class="inline-error" role="alert">{{ error }}</p>
    <p v-if="message" role="status">{{ message }}</p>
    <div class="dialog-footer">
      <Button variant="outline" :disabled="busy" @click="load"
        >重新加载外观</Button
      ><Button variant="outline" :disabled="busy" @click="preset('light')"
        >恢复默认</Button
      ><Button :disabled="busy || revision === null" @click="save"
        >保存外观</Button
      >
    </div>
  </section>
</template>
