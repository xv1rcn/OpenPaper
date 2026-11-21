import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath, URL } from "node:url";
export default defineConfig({
  base: "/app/",
  plugins: [
    vue(),
    tailwindcss(),
    {
      name: "pdfjs-local-assets",
      generateBundle() {
        this.emitFile({
          type: "asset",
          fileName: "pdfjs/LICENSE.txt",
          source: readFileSync(resolve("node_modules/pdfjs-dist/LICENSE")),
        });
        for (const folder of ["cmaps", "standard_fonts", "wasm"]) {
          const root = resolve("node_modules/pdfjs-dist", folder);
          for (const file of readdirSync(root)) {
            if (/\.(bcmap|pfb|ttf|wasm)$/.test(file))
              this.emitFile({
                type: "asset",
                fileName: `pdfjs/${folder}/${file}`,
                source: readFileSync(resolve(root, file)),
              });
          }
        }
      },
      configureServer(server) {
        server.middlewares.use("/app/pdfjs", (req, res, next) => {
          const match = (req.url || "").match(
            /^\/(cmaps|standard_fonts|wasm)\/([A-Za-z0-9_.-]+\.(?:bcmap|pfb|ttf|wasm))$/,
          );
          if (!match || match[2].includes("..")) return next();
          try {
            res.setHeader(
              "Content-Type",
              match[2].endsWith(".wasm")
                ? "application/wasm"
                : "application/octet-stream",
            );
            res.end(
              readFileSync(
                resolve("node_modules/pdfjs-dist", match[1], match[2]),
              ),
            );
          } catch {
            next();
          }
        });
      },
    },
  ],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
        configure(proxy) {
          proxy.on("proxyReq", (req) =>
            req.setHeader("Origin", "http://127.0.0.1:8001"),
          );
        },
      },
      "/papers": "http://127.0.0.1:8001",
    },
  },
});
