"use client";

import { ExternalLink, RefreshCw, Search, SlidersHorizontal, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

const GRAPHQL_URL = process.env.NEXT_PUBLIC_GRAPHQL_URL ?? "http://127.0.0.1:8001/graphql/";

const SEARCH_JOBS_QUERY = `
  query SearchJobs($query: String!, $skill: String, $location: String, $remote: Boolean, $limit: Int) {
    searchJobs(query: $query, skill: $skill, location: $location, remote: $remote, limit: $limit) {
      query
      correctedQuery
      selectedSkill
      total
      jobs {
        id
        title
        company
        location
        remoteAllowed
        workType
        experienceLevel
        descriptionSnippet
        postingUrl
        skills {
          name
          originalPhrase
        }
      }
      relatedSkills {
        name
        count
      }
      graph {
        nodes {
          id
          label
          type
        }
        edges {
          source
          target
          type
          weight
        }
      }
    }
  }
`;

type Skill = {
  name: string;
  originalPhrase: string;
};

type JobResult = {
  id: string;
  title: string;
  company: string;
  location: string;
  remoteAllowed: boolean;
  workType: string;
  experienceLevel: string;
  descriptionSnippet: string;
  postingUrl: string;
  skills: Skill[];
};

type RelatedSkill = {
  name: string;
  count: number;
};

type GraphNode = {
  id: string;
  label: string;
  type: string;
};

type GraphEdge = {
  source: string;
  target: string;
  type: string;
  weight: number;
};

type SearchPayload = {
  query: string;
  correctedQuery: string;
  selectedSkill: string;
  total: number;
  jobs: JobResult[];
  relatedSkills: RelatedSkill[];
  graph: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };
};

type GraphQLResponse = {
  data?: {
    searchJobs: SearchPayload;
  };
  errors?: Array<{ message: string }>;
};

type SearchInput = {
  query: string;
  skill: string;
  location: string;
  remote: "any" | "true" | "false";
};

type PositionedSkill = RelatedSkill & {
  left: number;
  top: number;
};

const defaultSearch: SearchInput = {
  query: "python backend engineer",
  skill: "",
  location: "",
  remote: "any"
};

export default function Home() {
  const [searchInput, setSearchInput] = useState<SearchInput>(defaultSearch);
  const [payload, setPayload] = useState<SearchPayload | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const didRunInitialSearch = useRef(false);

  const selectedJob = useMemo(() => {
    if (!payload?.jobs.length) {
      return null;
    }
    return payload.jobs.find((job) => job.id === selectedJobId) ?? payload.jobs[0];
  }, [payload, selectedJobId]);

  const maxRelatedCount = useMemo(() => {
    return Math.max(1, ...((payload?.relatedSkills ?? []).map((item) => item.count)));
  }, [payload]);

  const runSearch = useCallback(async (nextInput?: Partial<SearchInput>) => {
    const input = { ...searchInput, ...nextInput };
    const trimmedQuery = input.query.trim();
    if (!trimmedQuery) {
      setError("Add a search term before running a search.");
      setPayload(null);
      setSelectedJobId(null);
      return;
    }

    setSearchInput(input);
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(GRAPHQL_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
        body: JSON.stringify({
          query: SEARCH_JOBS_QUERY,
          variables: {
            query: trimmedQuery,
            skill: input.skill.trim() || null,
            location: input.location.trim() || null,
            remote: input.remote === "any" ? null : input.remote === "true",
            limit: 12
          }
        })
      });

      if (!response.ok) {
        throw new Error(`GraphQL request failed with status ${response.status}.`);
      }

      const body = (await response.json()) as GraphQLResponse;
      if (body.errors?.length) {
        throw new Error(body.errors.map((item) => item.message).join(" "));
      }
      if (!body.data?.searchJobs) {
        throw new Error("GraphQL response did not include search results.");
      }

      setPayload(body.data.searchJobs);
      setSelectedJobId(body.data.searchJobs.jobs[0]?.id ?? null);
    } catch (searchError) {
      setError(searchError instanceof Error ? searchError.message : "Search failed.");
      setPayload(null);
      setSelectedJobId(null);
    } finally {
      setLoading(false);
    }
  }, [searchInput]);

  useEffect(() => {
    if (!didRunInitialSearch.current) {
      didRunInitialSearch.current = true;
      void runSearch(defaultSearch);
    }
  }, [runSearch]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runSearch();
  }

  function updateInput<K extends keyof SearchInput>(key: K, value: SearchInput[K]) {
    setSearchInput((current) => ({ ...current, [key]: value }));
  }

  function applyRelatedSkill(skillName: string) {
    void runSearch({ skill: skillName });
  }

  function clearSkillFilter() {
    void runSearch({ skill: "" });
  }

  return (
    <main className="min-h-screen bg-paper text-ink">
      <header className="flex h-14 items-center justify-between border-b border-line bg-white px-5">
        <div className="text-base font-semibold">SkillScan</div>
        <div className="text-sm text-neutral-500">Job search and skill discovery</div>
      </header>

      <section className="border-b border-line bg-white px-5 py-4">
        <form onSubmit={handleSubmit} className="grid gap-3 lg:grid-cols-[minmax(360px,1fr)_190px_140px_110px]">
          <label className="flex h-10 items-center gap-3 rounded-md border border-line bg-white px-3">
            <Search size={17} className="text-neutral-500" />
            <input
              className="w-full bg-transparent text-sm outline-none"
              value={searchInput.query}
              onChange={(event) => updateInput("query", event.target.value)}
              aria-label="Search jobs"
              placeholder="Search by job title, company, keyword, or technology"
            />
          </label>
          <input
            className="h-10 rounded-md border border-line bg-white px-3 text-sm outline-none focus:border-neutral-500"
            value={searchInput.location}
            onChange={(event) => updateInput("location", event.target.value)}
            aria-label="Location filter"
            placeholder="Location"
          />
          <select
            className="h-10 rounded-md border border-line bg-white px-3 text-sm outline-none focus:border-neutral-500"
            value={searchInput.remote}
            onChange={(event) => updateInput("remote", event.target.value as SearchInput["remote"])}
            aria-label="Remote filter"
          >
            <option value="any">Any remote</option>
            <option value="true">Remote only</option>
            <option value="false">On-site only</option>
          </select>
          <button
            type="submit"
            className="flex h-10 items-center justify-center gap-2 rounded-md bg-ink px-4 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
            disabled={loading}
          >
            {loading ? <RefreshCw size={16} className="animate-spin" /> : <SlidersHorizontal size={16} />}
            Search
          </button>
        </form>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-neutral-600">
          {payload ? (
            <span>
              Showing {payload.jobs.length} of {payload.total} for{" "}
              <strong className="font-semibold text-ink">{payload.correctedQuery || payload.query}</strong>
            </span>
          ) : (
            <span>Connects to the local Django GraphQL API at {GRAPHQL_URL}</span>
          )}
          {payload && payload.query !== payload.correctedQuery ? (
            <span className="rounded-md border border-line px-2 py-1 text-xs">
              corrected from {payload.query}
            </span>
          ) : null}
          {searchInput.skill ? (
            <button
              className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs text-emerald-800"
              onClick={clearSkillFilter}
              type="button"
            >
              Skill filter: {searchInput.skill} x
            </button>
          ) : null}
        </div>
      </section>

      <section className="grid min-h-[calc(100vh-127px)] grid-cols-1 lg:grid-cols-[390px_minmax(520px,1fr)_360px]">
        <section className="border-r border-line bg-[#fbfaf7]">
          <div className="border-b border-line px-4 py-3">
            <h1 className="text-base font-semibold">Jobs</h1>
            <p className="mt-1 text-sm text-neutral-600">Openings that match the search and active filters.</p>
          </div>
          <div className="h-[calc(100vh-188px)] overflow-y-auto p-4">
            {error ? <StatusMessage title="Search failed" body={error} /> : null}
            {loading ? <StatusMessage title="Searching" body="Fetching jobs, skills, and graph context." /> : null}
            {!loading && !error && payload?.jobs.length === 0 ? (
              <StatusMessage
                title="No jobs returned"
                body="If this is a fresh database, run docker compose exec backend python manage.py bootstrap_demo --limit 1000."
              />
            ) : null}
            {!loading && !error && !payload ? (
              <StatusMessage title="No search loaded" body="Run a search to load jobs from the backend." />
            ) : null}
            <div className="space-y-3">
              {payload?.jobs.map((job) => (
                <button
                  key={job.id}
                  onClick={() => setSelectedJobId(job.id)}
                  className={`w-full rounded-md border bg-white p-4 text-left transition-colors ${
                    selectedJob?.id === job.id ? "border-ink" : "border-line hover:border-neutral-400"
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="font-semibold leading-5">{job.title}</div>
                      <div className="mt-1 text-sm text-neutral-600">
                        {job.company} - {job.location || "Location unavailable"}
                      </div>
                    </div>
                  </div>
                  <p className="mt-3 text-sm leading-5 text-neutral-700">{job.descriptionSnippet}</p>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {job.skills.slice(0, 5).map((item) => (
                      <span key={item.name} className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs text-emerald-800">
                        {item.name}
                      </span>
                    ))}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </section>

        <section className="min-h-[540px] border-r border-line bg-[#f9f8f4]">
          <div className="flex items-center justify-between border-b border-line bg-white px-4 py-3">
            <div>
              <h2 className="font-semibold">Skill Discovery</h2>
              <p className="text-sm text-neutral-600">
                {payload?.selectedSkill
                  ? `Skills that commonly appear with ${payload.selectedSkill}.`
                  : "Run a search to see related skills."}
              </p>
            </div>
          </div>
          <div className="grid h-[calc(100vh-188px)] min-h-[520px] grid-rows-[minmax(300px,1fr)_250px]">
            <SkillMap
              selectedSkill={payload?.selectedSkill ?? ""}
              relatedSkills={payload?.relatedSkills ?? []}
              onSelectSkill={applyRelatedSkill}
            />
            <aside className="border-t border-line bg-white p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-semibold">
                  {payload?.selectedSkill ? `Often appears with ${payload.selectedSkill}` : "Related skills"}
                </div>
                {payload?.selectedSkill ? (
                  <div className="text-xs text-neutral-500">
                    Click a skill to filter jobs
                  </div>
                ) : null}
              </div>
              <div className="mt-3 space-y-2">
                {payload?.relatedSkills.length ? (
                  payload.relatedSkills.map((item) => (
                    <button
                      key={item.name}
                      className="grid w-full grid-cols-[120px_1fr_58px] items-center gap-3 rounded-md border border-line px-3 py-2 text-left text-sm hover:border-neutral-400"
                      onClick={() => applyRelatedSkill(item.name)}
                    >
                      <span className="font-medium">{item.name}</span>
                      <span className="h-1.5 rounded bg-neutral-100">
                        <span
                          className="block h-1.5 rounded bg-skill"
                          style={{ width: `${Math.max(8, Math.round((item.count / maxRelatedCount) * 100))}%` }}
                        />
                      </span>
                      <span className="text-right text-neutral-500">{item.count} postings</span>
                    </button>
                  ))
                ) : (
                  <div className="rounded-md border border-line p-3 text-sm text-neutral-600">
                    No related skills were found for the current search.
                  </div>
                )}
              </div>
            </aside>
          </div>
        </section>

        <aside className="bg-white">
          <div className="flex items-start justify-between border-b border-line p-4">
            <div>
              <h2 className="font-semibold">Job Detail</h2>
              <p className="text-sm text-neutral-600">Selected search result.</p>
            </div>
            <button
              aria-label="Clear selected job"
              className="rounded-md p-1 text-neutral-500 hover:bg-neutral-100"
              onClick={() => setSelectedJobId(null)}
            >
              <X size={18} />
            </button>
          </div>
          {selectedJob ? (
            <div className="h-[calc(100vh-188px)] overflow-y-auto p-4">
              <div className="text-lg font-semibold leading-6">{selectedJob.title}</div>
              <div className="mt-1 text-sm text-neutral-600">
                {selectedJob.company} - {selectedJob.location || "Location unavailable"}
              </div>
              <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
                <InfoCell label="Remote" value={selectedJob.remoteAllowed ? "Yes" : "No"} />
                <InfoCell label="Work type" value={selectedJob.workType || "Unknown"} />
                <InfoCell label="Level" value={selectedJob.experienceLevel || "Unknown"} />
              </div>

              <div className="mt-5 text-sm font-semibold">Description</div>
              <p className="mt-2 text-sm leading-5 text-neutral-700">{selectedJob.descriptionSnippet}</p>

              <div className="mt-5 text-sm font-semibold">Skills found in this posting</div>
              <p className="mt-1 text-sm text-neutral-600">
                Left side is the saved skill. Right side is the phrase found in the job text.
              </p>
              <div className="mt-2 divide-y divide-line rounded-md border border-line">
                {selectedJob.skills.length ? (
                  selectedJob.skills.map((item) => (
                    <div key={item.name} className="grid grid-cols-[1fr_1fr] gap-3 px-3 py-2 text-sm">
                      <span className="font-medium">{item.name}</span>
                      <span className="text-right text-neutral-500">{item.originalPhrase || "description"}</span>
                    </div>
                  ))
                ) : (
                  <div className="px-3 py-2 text-sm text-neutral-600">No known skills were found in this posting.</div>
                )}
              </div>

              {selectedJob.postingUrl ? (
                <a
                  className="mt-5 flex h-10 items-center justify-center gap-2 rounded-md bg-ink px-3 text-sm font-medium text-white"
                  href={selectedJob.postingUrl}
                  target="_blank"
                  rel="noreferrer"
                >
                  View posting
                  <ExternalLink size={15} />
                </a>
              ) : null}
            </div>
          ) : (
            <div className="p-4">
              <StatusMessage title="No job selected" body="Choose a result to inspect its normalized skills and graph context." />
            </div>
          )}
        </aside>
      </section>
    </main>
  );
}

function SkillMap({
  selectedSkill,
  relatedSkills,
  onSelectSkill
}: {
  selectedSkill: string;
  relatedSkills: RelatedSkill[];
  onSelectSkill: (skillName: string) => void;
}) {
  const positionedSkills = useMemo(() => positionSkills(relatedSkills.slice(0, 8)), [relatedSkills]);

  if (!selectedSkill) {
    return (
      <div className="flex items-center justify-center p-6 text-center text-sm text-neutral-600">
        Skill relationships appear after search returns normalized skills.
      </div>
    );
  }

  return (
    <div className="relative min-h-0 overflow-hidden bg-[#f9f8f4]">
      <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        {positionedSkills.map((item) => (
          <line
            key={item.name}
            x1="50"
            y1="50"
            x2={item.left}
            y2={item.top}
            stroke="#c9c3b8"
            strokeWidth={Math.max(0.35, Math.min(1.3, item.count / 40))}
          />
        ))}
      </svg>

      <button
        className="absolute left-1/2 top-1/2 z-10 min-w-[120px] -translate-x-1/2 -translate-y-1/2 rounded-md border border-ink bg-white px-4 py-3 text-center text-sm font-semibold"
        onClick={() => onSelectSkill(selectedSkill)}
      >
        {selectedSkill}
      </button>

      {positionedSkills.map((item) => (
        <button
          key={item.name}
          className="absolute z-10 min-w-[104px] -translate-x-1/2 -translate-y-1/2 rounded-md border border-line bg-white px-3 py-2 text-left text-sm hover:border-neutral-400"
          style={{ left: `${item.left}%`, top: `${item.top}%` }}
          onClick={() => onSelectSkill(item.name)}
        >
          <span className="block font-medium">{item.name}</span>
          <span className="mt-0.5 block text-xs text-neutral-500">{item.count} postings</span>
        </button>
      ))}
    </div>
  );
}

function positionSkills(skills: RelatedSkill[]): PositionedSkill[] {
  if (!skills.length) {
    return [];
  }

  const radiusX = 34;
  const radiusY = 30;
  return skills.map((skill, index) => {
    const angle = -Math.PI / 2 + (index / skills.length) * Math.PI * 2;
    return {
      ...skill,
      left: Math.round((50 + Math.cos(angle) * radiusX) * 10) / 10,
      top: Math.round((50 + Math.sin(angle) * radiusY) * 10) / 10
    };
  });
}

function StatusMessage({ title, body }: { title: string; body: string }) {
  return (
    <div className="mb-3 rounded-md border border-line bg-white p-4">
      <div className="text-sm font-semibold">{title}</div>
      <div className="mt-1 text-sm leading-5 text-neutral-600">{body}</div>
    </div>
  );
}

function InfoCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-[#fbfaf7] p-3">
      <div className="text-xs text-neutral-500">{label}</div>
      <div className="mt-1 text-sm font-medium">{value}</div>
    </div>
  );
}
