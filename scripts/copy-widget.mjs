import { copyFileSync, mkdirSync } from "node:fs";
mkdirSync("../../apps/web/public", { recursive: true });
copyFileSync("dist/widget.js", "../../apps/web/public/widget.js");
