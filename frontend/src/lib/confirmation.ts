import { shallowRef } from "vue";
export const confirmation = shallowRef<{
  description: string;
  action: string;
  resolve: (value: boolean) => void;
} | null>(null);
export function confirmAction(
  description: string,
  action = "放弃修改",
): Promise<boolean> {
  if (confirmation.value) return Promise.resolve(false);
  return new Promise((resolve) => {
    confirmation.value = { description, action, resolve };
  });
}
export function finishConfirmation(value: boolean) {
  const current = confirmation.value;
  confirmation.value = null;
  current?.resolve(value);
}
