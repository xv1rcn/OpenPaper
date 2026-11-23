<script setup lang="ts">
import {
  AlertDialogRoot,
  AlertDialogPortal,
  AlertDialogOverlay,
  AlertDialogContent,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogCancel,
} from "reka-ui";
import { confirmation, finishConfirmation } from "@/lib/confirmation";
</script>
<template>
  <AlertDialogRoot
    :open="!!confirmation"
    @update:open="
      (value) => {
        if (!value) finishConfirmation(false);
      }
    "
  >
    <AlertDialogPortal>
      <AlertDialogOverlay class="dialog-overlay confirmation-overlay" />
      <AlertDialogContent class="dialog-content confirmation-dialog">
        <AlertDialogTitle class="dialog-title">{{
          confirmation?.action
        }}</AlertDialogTitle>
        <AlertDialogDescription class="confirmation-description">{{
          confirmation?.description
        }}</AlertDialogDescription>
        <div class="dialog-footer">
          <AlertDialogCancel
            class="ui-button button-outline"
            @click="finishConfirmation(false)"
            >取消</AlertDialogCancel
          >
          <button type="button"
            class="ui-button button-primary"
            @click="finishConfirmation(true)"
            >{{ confirmation?.action }}</button
          >
        </div>
      </AlertDialogContent>
    </AlertDialogPortal>
  </AlertDialogRoot>
</template>
