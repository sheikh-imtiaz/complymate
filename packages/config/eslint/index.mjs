// Shared flat ESLint config for the Next.js apps.
import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({ baseDirectory: import.meta.dirname });

export default [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    rules: {
      "@typescript-eslint/no-explicit-any": "warn",
      "no-console": ["warn", { allow: ["warn", "error"] }],
      "react/no-danger": "error",
    },
  },
  { ignores: [".next/**", "node_modules/**", "playwright-report/**"] },
];
