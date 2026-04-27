import { nodeResolve } from "@rollup/plugin-node-resolve";
import typescript from "@rollup/plugin-typescript";

export default {
  input: "src/battery-notes-panel.ts",
  output: {
    file: "dist/battery-notes-panel.js",
    format: "es",
    sourcemap: false
  },
  plugins: [
    nodeResolve(),
    typescript({
      tsconfig: "./tsconfig.json"
    })
  ]
};
