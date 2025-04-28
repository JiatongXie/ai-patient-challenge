import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 从环境变量或默认值获取允许的主机列表
const getAllowedHosts = () => {
  const envHosts = process.env.VITE_ALLOWED_HOSTS;
  const defaultHosts = ["localhost"];
  return envHosts ? [...defaultHosts, ...envHosts.split(",")] : defaultHosts;
};

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    allowedHosts: getAllowedHosts(),
    proxy: {
      "/api": {
        target: "http://localhost:5001",
        changeOrigin: true,
        secure: false,
        ws: true,
        configure: (proxy, _options) => {
          proxy.on("error", (err, _req, _res) => {
            console.log("proxy error", err);
          });
          proxy.on("proxyReq", (proxyReq, req, _res) => {
            console.log("Sending Request to the Target:", req.method, req.url);
          });
          proxy.on("proxyRes", (proxyRes, req, _res) => {
            console.log(
              "Received Response from the Target:",
              proxyRes.statusCode,
              req.url
            );
          });
        },
      },
    },
  },
  build: {
    outDir: "build",
  },
  resolve: {
    extensions: [".js", ".jsx", ".json"],
  },
  esbuild: {
    loader: "jsx",
    include: /src\/.*\.jsx?$/,
    exclude: [],
  },
  optimizeDeps: {
    esbuildOptions: {
      loader: {
        ".js": "jsx",
      },
    },
  },
});
