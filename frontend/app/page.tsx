"use client";

import { Search, SlidersHorizontal, X } from "lucide-react";
import dynamic from "next/dynamic";
import { useMemo, useState } from "react";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

const jobs = [
  {
    id: "1",
    title: "Backend Engineer, Python Platform",
    company: "Stripe",
    location: "New York, NY / Remote",
    score: 98,
    skills: ["Python", "Django", "PostgreSQL"],
    snippet: "Build backend services for payment infrastructure with Python APIs and relational data systems.",
    reason: "matched Python, backend APIs, PostgreSQL"
  },
  {
    id: "2",
    title: "Django Backend Developer",
    company: "HealthTech Labs",
    location: "Boston, MA",
    score: 93,
    skills: ["Python", "Django", "Docker"],
    snippet: "Ship Django REST APIs for clinical workflow products and data-heavy internal tools.",
    reason: "matched Django REST APIs"
  },
  {
    id: "3",
    title: "Search Infrastructure Engineer",
    company: "Spotify",
    location: "Remote",
    score: 89,
    skills: ["Python", "Elasticsearch", "AWS"],
    snippet: "Improve search ranking pipelines and indexing workflows across large content datasets.",
    reason: "matched search and Elasticsearch"
  },
  {
    id: "4",
    title: "Graph Systems Engineer",
    company: "NeoWorks",
    location: "Remote",
    score: 84,
    skills: ["Python", "Neo4j", "GraphQL"],
    snippet: "Model entity relationships and expose graph-backed discovery APIs for internal users.",
    reason: "matched graph relationships"
  }
];

const related = [
  ["Django", 82],
  ["PostgreSQL", 76],
  ["FastAPI", 64],
  ["Docker", 61],
  ["AWS", 58]
] as const;

export default function Home() {
  const [selectedJob, setSelectedJob] = useState(jobs[0]);
  const graphData = useMemo(
    () => ({
      nodes: [
        { id: "Python", group: "skill" },
        { id: "Django", group: "skill" },
        { id: "PostgreSQL", group: "skill" },
        { id: "FastAPI", group: "skill" },
        { id: "Docker", group: "skill" },
        { id: "AWS", group: "skill" },
        { id: "Elasticsearch", group: "skill" },
        { id: "Stripe", group: "company" },
        { id: "Backend Engineer", group: "job" }
      ],
      links: [
        { source: "Python", target: "Django" },
        { source: "Python", target: "PostgreSQL" },
        { source: "Python", target: "FastAPI" },
        { source: "Python", target: "Docker" },
        { source: "Python", target: "AWS" },
        { source: "Python", target: "Elasticsearch" },
        { source: "Stripe", target: "Backend Engineer" },
        { source: "Backend Engineer", target: "Python" }
      ]
    }),
    []
  );

  return (
    <main className="min-h-screen bg-paper">
      <header className="flex h-14 items-center justify-between border-b border-line bg-white px-6">
        <div className="text-base font-semibold tracking-tight">SkillScan</div>
        <div className="text-sm text-neutral-500">LinkedIn sample: 10,000 postings</div>
      </header>

      <section className="border-b border-line bg-white px-6 py-4">
        <div className="flex gap-3">
          <label className="flex h-11 flex-1 items-center gap-3 rounded-md border border-line bg-white px-3">
            <Search size={18} className="text-neutral-500" />
            <input
              className="w-full outline-none"
              defaultValue="pythn backend engineer"
              aria-label="Search jobs"
            />
          </label>
          <button className="rounded-md bg-ink px-5 text-sm font-medium text-white">Search</button>
        </div>
        <div className="mt-3 flex items-center justify-between text-sm">
          <span className="text-neutral-600">
            Showing results for <strong className="text-ink">python backend engineer</strong>
          </span>
          <div className="flex items-center gap-2">
            <Filter label="Skill" value="Python" />
            <Filter label="Location" value="Any" />
            <Filter label="Remote" value="Yes" />
            <button className="flex h-8 items-center gap-2 rounded-md border border-line bg-white px-3 text-neutral-700">
              <SlidersHorizontal size={15} />
              Refine
            </button>
          </div>
        </div>
      </section>

      <section className="grid h-[calc(100vh-126px)] grid-cols-[minmax(420px,0.9fr)_minmax(520px,1.1fr)] gap-0">
        <div className="overflow-y-auto border-r border-line bg-[#fbfaf7] px-5 py-5">
          <div className="mb-4 flex items-end justify-between">
            <div>
              <h1 className="text-xl font-semibold tracking-tight">1,284 matching jobs</h1>
              <p className="mt-1 text-sm text-neutral-600">Ranked by text relevance and extracted skill overlap.</p>
            </div>
          </div>

          <div className="space-y-3">
            {jobs.map((job) => (
              <button
                key={job.id}
                onClick={() => setSelectedJob(job)}
                className={`w-full rounded-lg border bg-white p-4 text-left transition-colors ${
                  selectedJob.id === job.id ? "border-ink" : "border-line hover:border-neutral-400"
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="font-semibold">{job.title}</div>
                    <div className="mt-1 text-sm text-neutral-600">
                      {job.company} · {job.location}
                    </div>
                  </div>
                  <div className="text-sm font-semibold text-job">{job.score}%</div>
                </div>
                <p className="mt-3 text-sm leading-5 text-neutral-700">{job.snippet}</p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {job.skills.map((skill) => (
                    <span key={skill} className="rounded border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs text-emerald-800">
                      {skill}
                    </span>
                  ))}
                </div>
                <div className="mt-3 text-xs text-neutral-500">{job.reason}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="relative bg-[#f9f8f4] p-5">
          <div className="flex h-full flex-col rounded-lg border border-line bg-white">
            <div className="flex items-center justify-between border-b border-line px-4 py-3">
              <div>
                <h2 className="font-semibold">Skill graph: Python</h2>
                <p className="text-sm text-neutral-600">Neo4j relationships from matched postings</p>
              </div>
              <div className="flex gap-2 text-xs text-neutral-600">
                <span className="text-skill">Skill</span>
                <span className="text-job">Job</span>
                <span className="text-company">Company</span>
              </div>
            </div>
            <div className="grid min-h-0 flex-1 grid-cols-[1fr_220px]">
              <div className="min-h-0 border-r border-line">
                <ForceGraph2D
                  graphData={graphData}
                  nodeLabel="id"
                  nodeAutoColorBy="group"
                  backgroundColor="#ffffff"
                  linkColor={() => "#c9c3b8"}
                  nodeCanvasObject={(node, ctx, globalScale) => {
                    const label = String(node.id);
                    const fontSize = Math.max(10, 13 / globalScale);
                    ctx.font = `${fontSize}px Aptos, sans-serif`;
                    ctx.fillStyle = node.id === "Python" ? "#20201d" : "#138a63";
                    ctx.beginPath();
                    ctx.arc(node.x || 0, node.y || 0, node.id === "Python" ? 8 : 5, 0, 2 * Math.PI, false);
                    ctx.fill();
                    ctx.fillStyle = "#20201d";
                    ctx.fillText(label, (node.x || 0) + 9, (node.y || 0) + 4);
                  }}
                />
              </div>
              <aside className="p-4">
                <div className="text-sm font-semibold">Selected skill</div>
                <div className="mt-1 text-lg font-semibold text-skill">Python</div>
                <div className="mt-5 text-sm font-semibold">Related skills</div>
                <div className="mt-3 space-y-3">
                  {related.map(([name, value]) => (
                    <div key={name}>
                      <div className="flex justify-between text-sm">
                        <span>{name}</span>
                        <span className="text-neutral-500">{value}%</span>
                      </div>
                      <div className="mt-1 h-1.5 rounded bg-neutral-100">
                        <div className="h-1.5 rounded bg-skill" style={{ width: `${value}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </aside>
            </div>
          </div>

          <aside className="absolute right-5 top-5 flex h-[calc(100%-40px)] w-[360px] flex-col rounded-lg border border-neutral-300 bg-white shadow-sm">
            <div className="flex items-start justify-between border-b border-line p-4">
              <div>
                <div className="text-lg font-semibold">{selectedJob.title}</div>
                <div className="mt-1 text-sm text-neutral-600">
                  {selectedJob.company} · {selectedJob.location}
                </div>
              </div>
              <button aria-label="Close drawer" className="rounded p-1 text-neutral-500 hover:bg-neutral-100">
                <X size={18} />
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-4">
              <div className="text-sm font-semibold">Description</div>
              <p className="mt-2 text-sm leading-5 text-neutral-700">{selectedJob.snippet}</p>

              <div className="mt-5 text-sm font-semibold">Skill normalization</div>
              <div className="mt-2 divide-y divide-line rounded-md border border-line">
                {selectedJob.skills.map((skill) => (
                  <div key={skill} className="flex justify-between px-3 py-2 text-sm">
                    <span>{skill}</span>
                    <span className="text-neutral-500">from description</span>
                  </div>
                ))}
              </div>

              <div className="mt-5 text-sm font-semibold">Match explanation</div>
              <p className="mt-2 rounded-md border border-line bg-[#fbfaf7] p-3 text-sm leading-5 text-neutral-700">
                {selectedJob.reason}. This posting also shares graph context with Django, PostgreSQL, and Docker.
              </p>
            </div>
            <div className="flex gap-2 border-t border-line p-4">
              <button className="flex-1 rounded-md bg-ink px-3 py-2 text-sm font-medium text-white">View posting</button>
              <button className="flex-1 rounded-md border border-line px-3 py-2 text-sm font-medium">Focus graph</button>
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}

function Filter({ label, value }: { label: string; value: string }) {
  return (
    <button className="rounded-md border border-line bg-white px-3 py-1.5 text-sm text-neutral-700">
      {label}: <span className="font-medium text-ink">{value}</span>
    </button>
  );
}
