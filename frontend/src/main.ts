import { createApp } from "vue";
import App from "./App.vue";
import "./style.css";
import { loadAppearance } from "./lib/preferences";
import { loadViewState } from "./lib/view-state";
loadAppearance();
loadViewState().finally(() => createApp(App).mount("#app"));
