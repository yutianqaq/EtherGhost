import "./assets/main.css";

import { createApp } from "vue";
import App from "./App.vue";

import Settings from "./components/Settings.vue";
import WebshellEditorMain from "./components/WebshellEditorMain.vue";
import HomeMain from "./components/HomeMain.vue";
import TerminalMain from "./components/TerminalMain.vue";
import FileBrowserMain from "./components/FileBrowserMain.vue";
import PhpEvalMain from "./components/PhpEvalMain.vue";
import { createRouter, createWebHashHistory } from "vue-router";

const routes = [
  { path: "/", component: HomeMain, props: true },
  {
    path: "/webshell-editor/:session",
    component: WebshellEditorMain,
    props: true,
  },
  {
    path: "/webshell-editor/",
    component: WebshellEditorMain,
    props: true,
  },
  {
    path: "/settings/",
    component: Settings,
    props: true,
  },
  { path: "/terminal/:session", component: TerminalMain, props: true },
  { path: "/file-browser/:session", component: FileBrowserMain, props: true },
  { path: "/php-eval/:session", component: PhpEvalMain, props: true },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

createApp(App).use(router).mount("#app");
