// Seed roadmap skill-trees into the backend from the frontend mock JSON files.
// The trees carry the source-of-truth `edges`; where a mock only has legacy
// `prereqs` on nodes, we derive edges from them. Run once after the DB is up:
//
//   node scripts/seed_roadmaps.mjs [API_BASE]
//
// Defaults to http://localhost:8080/api. Registers (or logs in) a faculty
// account, then PUTs each tree via PUT /api/roadmaps/{id}.

import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const API = (process.argv[2] || "http://localhost:8080/api").replace(/\/$/, "");
const here = dirname(fileURLToPath(import.meta.url));
const MOCKS = resolve(here, "../../frontend/public/mocks");
const IDS = ["frontend", "backend", "data", "mobile"];

const FACULTY = {
  email: "seed-faculty@sepaham.local",
  password: "seedfaculty123",
  name: "Seed Faculty",
  role: "faculty",
};

async function getToken() {
  // Try register; if the account already exists, log in instead.
  let res = await fetch(`${API}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(FACULTY),
  });
  if (res.status === 409) {
    res = await fetch(`${API}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: FACULTY.email, password: FACULTY.password }),
    });
  }
  if (!res.ok) throw new Error(`auth failed: ${res.status} ${await res.text()}`);
  return (await res.json()).token;
}

/** Build edges: explicit `edges` win; otherwise derive from node.prereqs. */
function edgesFor(tree) {
  if (Array.isArray(tree.edges) && tree.edges.length) return tree.edges;
  const edges = [];
  for (const node of tree.nodes ?? []) {
    for (const prereq of node.prereqs ?? []) {
      edges.push({ id: `e-${prereq}-${node.id}`, source: prereq, target: node.id });
    }
  }
  return edges;
}

async function seedOne(token, id) {
  const raw = await readFile(resolve(MOCKS, `roadmap-${id}.json`), "utf8");
  const tree = JSON.parse(raw);
  const body = {
    roleId: tree.roleId ?? null,
    title: tree.title,
    emoji: tree.emoji ?? "",
    author: tree.author ?? "",
    style: tree.style ?? {},
    nodes: tree.nodes ?? [],
    edges: edgesFor(tree),
  };
  const res = await fetch(`${API}/roadmaps/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`seed ${id} failed: ${res.status} ${await res.text()}`);
  console.log(`  ✓ ${id}: ${body.nodes.length} nodes, ${body.edges.length} edges`);
}

const token = await getToken();
console.log(`Seeding roadmaps into ${API} ...`);
for (const id of IDS) await seedOne(token, id);
console.log("Done.");
