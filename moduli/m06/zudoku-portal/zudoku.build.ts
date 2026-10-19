import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, watchFile, writeFileSync } from "node:fs";
import { basename, resolve } from "node:path";

// PlantUML sources rendered into the description of an operation, keyed "METHOD /path".
// The .puml files are the source of truth: the SVG is regenerated on every build and dev start,
// and while the dev server runs.
const DIAGRAMS: Record<string, { source: string; title: string }> = {
  "post /payments": {
    source: "../../../caso-guida/req-seq-payment-retry.puml",
    title: "Payment retry sequence",
  },
};

// Render through the PlantUML server started by ../scripts/plantuml-server.sh (npm run plantuml:start).
const SERVER = process.env.PLANTUML_SERVER ?? "http://127.0.0.1:18080";

const renderSvg = async (puml: string): Promise<string> => {
  const hex = Buffer.from(puml, "utf8").toString("hex");
  try {
    const response = await fetch(`${SERVER}/svg/~h${hex}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.text();
  } catch (error) {
    throw new Error(
      `Cannot render PlantUML with the server at ${SERVER}. Start it with "npm run plantuml:start". ${error}`,
    );
  }
};

// PlantUML sets a fixed pixel size; scale it down to fit the reference column.
const MAX_WIDTH = 480;
const fitWidth = (svg: string): string =>
  svg.replace(/<svg [^>]*>/, (tag) => {
    const [, width, height] = tag.match(/viewBox="0 0 (\d+) (\d+)"/) ?? [];
    if (!width || Number(width) <= MAX_WIDTH) return tag;
    const scale = MAX_WIDTH / Number(width);
    return tag
      .replace(/ style="[^"]*"/, "")
      .replace(/ width="[^"]*"/, ` width="${MAX_WIDTH}"`)
      .replace(/ height="[^"]*"/, ` height="${Math.round(Number(height) * scale)}"`);
  });

const addDiagrams = async ({ schema }: { schema: any }) => {
  mkdirSync("public/diagrams", { recursive: true });
  for (const [key, { source, title }] of Object.entries(DIAGRAMS)) {
    const [method, path] = key.split(" ");
    const operation = schema.paths?.[path]?.[method];
    if (!operation) continue;
    const file = `${basename(source, ".puml")}.svg`;
    const render = async () =>
      writeFileSync(`public/diagrams/${file}`, fitWidth(await renderSvg(readFileSync(resolve(source), "utf8"))));
    await render();
    // In `npm run dev`, render again when the .puml changes (reload the page to see it).
    // unref() keeps the watcher from holding the build process open.
    watchFile(resolve(source), { interval: 500 }, () => render().catch(console.error)).unref();
    operation.description = `${operation.description ?? ""}\n\n![${title}](/diagrams/${file})`;
  }
  return schema;
};

export default { processors: [addDiagrams] };
