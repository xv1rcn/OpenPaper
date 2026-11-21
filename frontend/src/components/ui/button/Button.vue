<script setup lang="ts">
import { Primitive, type PrimitiveProps } from "reka-ui";
import { cva } from "class-variance-authority";
import { cn } from "@/lib/utils";
const props = withDefaults(
  defineProps<
    PrimitiveProps & {
      variant?: "default" | "ghost" | "outline";
      class?: string;
    }
  >(),
  { as: "button", variant: "default" },
);
const variants = cva("ui-button", {
  variants: {
    variant: {
      default: "button-primary",
      ghost: "button-ghost",
      outline: "button-outline",
    },
  },
});
</script>
<template>
  <Primitive
    :as="props.as"
    :as-child="props.asChild"
    :class="cn(variants({ variant }), props.class)"
    ><slot
  /></Primitive>
</template>
