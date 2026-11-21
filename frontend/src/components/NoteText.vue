<script setup lang="ts">
import { computed } from "vue";
const props = defineProps<{ text: string }>();
const parts = computed(() =>
  props.text
    .split(/(https?:\/\/[^\s<>"'）)\]，。；]+)/g)
    .map((text) => ({ text, link: /^https?:\/\//.test(text) })),
);
</script>
<template>
  <span class="note-text"
    ><template v-for="(part, index) in parts" :key="index"
      ><a
        v-if="part.link"
        :href="part.text"
        target="_blank"
        rel="noopener noreferrer"
        >{{ part.text }}</a
      ><template v-else>{{ part.text }}</template></template
    ></span
  >
</template>
