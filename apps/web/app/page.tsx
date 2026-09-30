import { getApiHealth } from "@/lib/api";

export const dynamic = "force-dynamic";

const capabilities = [
  "Tenant-aware authentication",
  "Document ingestion + pgvector",
  "Grounded AI chat",
  "Agent orchestration",
  "MCP tools",
  "Human approvals",
];

export default async function Home() {
  const health = await getApiHealth();
  const apiOnline = health?.status === "ok";

  return (
    <main>
      <section className="hero">
        <div className="eyebrow">AI-NATIVE OPERATIONS PLATFORM</div>
        <h1>
          Reliable AI agents for
          <span> real operational work.</span>
        </h1>
        <p className="lede">
          AgentOps AI is being built as a production-oriented platform for
          knowledge retrieval, incident analysis, tool execution, and
          human-approved automation.
        </p>

        <div className="actions">
          <a className="primary" href="#architecture">
            Explore architecture
          </a>
          <a
            className="secondary"
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
          >
            Open API docs
          </a>
        </div>
      </section>

      <section className="status-grid" aria-label="Platform status">
        <article className="card accent">
          <span className="label">Phase</span>
          <strong>04 / Retrieval</strong>
          <p>Document ingestion, pgvector, HNSW, and tenant-safe search.</p>
        </article>

        <article className="card">
          <span className="label">API</span>
          <strong className={apiOnline ? "online" : "offline"}>
            {apiOnline ? "Healthy" : "Unavailable"}
          </strong>
          <p>
            {apiOnline
              ? `FastAPI ${health?.version} responded successfully.`
              : "Start the API to enable live health verification."}
          </p>
        </article>

        <article className="card">
          <span className="label">Engineering rule</span>
          <strong>Verify, then trust.</strong>
          <p>Every capability must be implemented, tested, and observable.</p>
        </article>
      </section>

      <section id="architecture" className="section">
        <div>
          <span className="label">Capabilities</span>
          <h2>Built to cover the full AI application lifecycle.</h2>
        </div>

        <div className="capability-grid">
          {capabilities.map((capability) => (
            <div className="capability" key={capability}>
              <span className="dot" />
              {capability}
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
