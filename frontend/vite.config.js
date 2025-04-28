import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// 使用函数式配置以便访问环境变量
export default defineConfig(({ mode }) => {
  // 加载环境变量
  const env = loadEnv(mode, process.cwd());

  // 从环境变量获取允许的主机列表，只有localhost是默认允许的
  const envHosts = env.VITE_ALLOWED_HOSTS;
  const allowedHosts = envHosts
    ? ["localhost", ...envHosts.split(",")]
    : ["localhost"];

  return {
    plugins: [react()],
    server: {
      port: 3000,
      host: "0.0.0.0",
      allowedHosts,
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
              console.log(
                "Sending Request to the Target:",
                req.method,
                req.url
              );
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
  };
});
