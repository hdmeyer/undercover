import { rmSync } from "node:fs";

rmSync(new URL("./test.db", import.meta.url), { force: true });
