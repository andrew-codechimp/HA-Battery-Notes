import typescript from "@rollup/plugin-typescript";

export default {
  input: "src/battery-notes-panel.ts",
  output: {
    file: "dist/battery-notes-panel.js",
    format: "es",
    sourcemap: false
  },
  plugins: [
    typescript({
      tsconfig: "./tsconfig.json"
    })
  ]
};
