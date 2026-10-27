import type { ZudokuConfig } from "zudoku";

const config: ZudokuConfig = {
  site: { title: "Checkout API portal" },
  navigation: [
    { type: "category", label: "Guides", items: ["introduction", "errors-and-retries"] },
    { type: "link", to: "/api", label: "API reference" },
  ],
  apis: {
    type: "file",
    input: "../../m07/openapi/checkout-api.yaml",
    path: "/api",
  },
};

export default config;
