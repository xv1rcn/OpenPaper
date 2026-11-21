import { createApp } from "vue";
import App from "./App.vue";
import "./style.css";
import { loadAppearance } from "./lib/preferences";
loadAppearance();
createApp(App).mount("#app");
