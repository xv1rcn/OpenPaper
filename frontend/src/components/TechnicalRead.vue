<script setup lang="ts">
import { computed } from "vue";
import { hasReadingContent } from "@/lib/reading";
import StructuredRead from "./StructuredRead.vue";
const props = defineProps<{ value: unknown }>();
defineEmits<{ page: [value: number] }>();
const content = computed(
  () =>
    (props.value &&
    typeof props.value === "object" &&
    !Array.isArray(props.value)
      ? props.value
      : { summary: props.value }) as Record<string, unknown>,
);
function records(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value)
    ? value
        .filter(hasReadingContent)
        .map((item) =>
          typeof item === "object" && item !== null
            ? (item as Record<string, unknown>)
            : { name: item },
        )
    : [];
}
const modules = computed(() => records(content.value.modules));
const terms = computed(() => records(content.value.terms));
function paragraphs(module: Record<string, unknown>) {
  // Only remove exact duplicate prose; do not rewrite evidence or inferred explanations.
  return [
    ...new Set(
      [module.role, module.mechanism, module.technical_explanation].filter(
        hasReadingContent,
      ),
    ),
  ];
}
function pages(value: unknown): number[] {
  return Array.isArray(value)
    ? [
        ...new Set(
          value
            .map(Number)
            .filter((page) => Number.isInteger(page) && page > 0),
        ),
      ]
    : [];
}
</script>
<template>
  <div class="technical-reading">
    <StructuredRead
      v-if="hasReadingContent(content.summary)"
      :value="content.summary"
      @page="$emit('page', $event)"
    />
    <section
      v-for="(module, index) in modules"
      :key="index"
      class="technical-module"
    >
      <h3>{{ module.name || `方法模块 ${index + 1}` }}</h3>
      <StructuredRead
        v-for="(paragraph, part) in paragraphs(module)"
        :key="part"
        :value="paragraph"
        @page="$emit('page', $event)"
      />
      <p
        v-if="
          Array.isArray(module.terms) &&
          module.terms.filter(hasReadingContent).length
        "
        class="reading-related-terms"
      >
        相关术语：{{ module.terms.filter(hasReadingContent).join("、") }}
      </p>
      <nav
        v-if="pages(module.page_refs).length"
        class="reading-references"
        :aria-label="`${module.name || '方法模块'}原文页码`"
      >
        <button
          v-for="page in pages(module.page_refs)"
          :key="page"
          class="page-reference"
          @click="$emit('page', page)"
        >
          第 {{ page }} 页
        </button>
      </nav>
    </section>
    <details v-if="terms.length" class="reading-glossary">
      <summary>
        术语解释 <span>{{ terms.length }}</span>
      </summary>
      <dl>
        <div v-for="(term, index) in terms" :key="index" class="reading-term">
          <dt>
            {{ term.term || term.name || `术语 ${index + 1}`
            }}<span
              v-if="term.basis === 'general_background'"
              class="reading-term-basis"
              >背景知识</span
            >
          </dt>
          <dd>
            <StructuredRead :value="term.explanation" /><StructuredRead
              v-if="hasReadingContent(term.paper_context)"
              :value="term.paper_context"
            />
          </dd>
        </div>
      </dl>
    </details>
    <section
      v-if="hasReadingContent(content.background_notes)"
      class="reading-supplement"
    >
      <h3>背景知识</h3>
      <StructuredRead
        :value="content.background_notes"
        @page="$emit('page', $event)"
      />
    </section>
    <section
      v-if="hasReadingContent(content.missing_details)"
      class="reading-supplement"
    >
      <h3>尚未交代的细节</h3>
      <StructuredRead
        :value="content.missing_details"
        @page="$emit('page', $event)"
      />
    </section>
  </div>
</template>
