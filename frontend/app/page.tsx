"use client";

import {
  BriefcaseBusiness,
  Check,
  ExternalLink,
  Network,
  RefreshCw,
  Search,
  Target,
  X
} from "lucide-react";
import { FormEvent, ReactNode, useCallback, useMemo, useState } from "react";

const GRAPHQL_URL = process.env.NEXT_PUBLIC_GRAPHQL_URL ?? "http://127.0.0.1:8001/graphql/";

const CAREER_MAP_QUERY = `
  query CareerMap($query: String!, $selectedSkills: [String!]!, $remote: Boolean, $limit: Int) {
    careerMap(query: $query, selectedSkills: $selectedSkills, remote: $remote, limit: $limit) {
      query
      correctedQuery
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
      marketSkills {
        name
        count
      }
      recommendedSkills {
        name
        count
        previewJobs {
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

type MarketSkill = {
  name: string;
  count: number;
};

type RecommendedSkill = {
  name: string;
  count: number;
  previewJobs: JobResult[];
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

type CareerMapPayload = {
  query: string;
  correctedQuery: string;
  total: number;
  jobs: JobResult[];
  marketSkills: MarketSkill[];
  recommendedSkills: RecommendedSkill[];
  graph: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };
};

type GraphQLResponse = {
  data?: {
    careerMap?: CareerMapPayload;
  };
  errors?: Array<{ message: string }>;
};

type SearchInput = {
  query: string;
  remote: "any" | "true" | "false";
};

type PositionedNode = GraphNode & {
  left: number;
  top: number;
};

const defaultSearch: SearchInput = {
  query: "",
  remote: "any"
};

export default function Home() {
  const [searchInput, setSearchInput] = useState<SearchInput>(defaultSearch);
  const [payload, setPayload] = useState<CareerMapPayload | null>(null);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filteredJobs = useMemo(() => {
    if (!payload?.jobs.length) {
      return [];
    }
    if (!selectedSkills.length) {
      return payload.jobs;
    }
    return jobsMatchingSkills(payload.jobs, selectedSkills);
  }, [payload, selectedSkills]);

  const selectedJob = useMemo(() => {
    if (!filteredJobs.length) {
      return null;
    }
    return filteredJobs.find((job) => job.id === selectedJobId) ?? filteredJobs[0];
  }, [filteredJobs, selectedJobId]);

  const maxRelatedJobCount = useMemo(() => {
    return Math.max(1, ...((payload?.recommendedSkills ?? []).map((skill) => skill.count)));
  }, [payload]);

  const runCareerMap = useCallback(
    async (nextInput?: Partial<SearchInput>, nextSelectedSkills?: string[]) => {
      const input = { ...searchInput, ...nextInput };
      const activeSelectedSkills = nextSelectedSkills ?? selectedSkills;
      const trimmedQuery = input.query.trim();
      if (!trimmedQuery) {
        setError("Enter a role, skill, or keyword to map the market.");
        setPayload(null);
        setSelectedJobId(null);
        return;
      }

      setSearchInput(input);
      setSelectedSkills(activeSelectedSkills);
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(GRAPHQL_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          cache: "no-store",
          body: JSON.stringify({
            query: CAREER_MAP_QUERY,
            variables: {
              query: trimmedQuery,
              selectedSkills: activeSelectedSkills,
              remote: input.remote === "any" ? null : input.remote === "true",
              limit: 24
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
        if (!body.data?.careerMap) {
          throw new Error("GraphQL response did not include a career map.");
        }

        const nextPayload = body.data.careerMap;
        const nextFilteredJobs = activeSelectedSkills.length
          ? jobsMatchingSkills(nextPayload.jobs, activeSelectedSkills)
          : nextPayload.jobs;
        setPayload(nextPayload);
        setSelectedJobId(nextFilteredJobs[0]?.id ?? null);
      } catch (searchError) {
        setError(searchError instanceof Error ? searchError.message : "Career map failed.");
        setPayload(null);
        setSelectedJobId(null);
      } finally {
        setLoading(false);
      }
    },
    [selectedSkills, searchInput]
  );

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSelectedSkills([]);
    void runCareerMap(undefined, []);
  }

  function updateInput<K extends keyof SearchInput>(key: K, value: SearchInput[K]) {
    setSearchInput((current) => ({ ...current, [key]: value }));
  }

  function toggleSelectedSkill(skillName: string) {
    const nextSelectedSkills = selectedSkills.some((skill) => sameSkill(skill, skillName))
      ? selectedSkills.filter((skill) => !sameSkill(skill, skillName))
      : [...selectedSkills, skillName];
    void runCareerMap(undefined, nextSelectedSkills);
  }

  return (
    <main className="flex h-screen flex-col overflow-hidden bg-[linear-gradient(135deg,#f7faf6_0%,#edf4ee_48%,#f8f5ec_100%)] text-ink">
      <header className="flex h-16 shrink-0 items-center justify-between border-b border-white/70 bg-white/75 px-6 backdrop-blur">
        <div className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/80 bg-white/80 text-skill shadow-sm">
            <Network size={18} />
          </span>
          <div className="text-base font-semibold">SkillScan</div>
        </div>
        <div className="text-sm text-neutral-500">Lightweight skill market lab</div>
      </header>

      <section className="shrink-0 border-b border-white/70 bg-white/45 px-6 py-5 backdrop-blur">
        <form onSubmit={handleSubmit} className="grid gap-3 rounded-2xl border border-white/80 bg-white/70 p-2 shadow-sm backdrop-blur lg:grid-cols-[minmax(360px,1fr)_150px_116px]">
          <label className="flex h-11 items-center gap-3 rounded-xl border border-transparent bg-white/80 px-3">
            <Search size={17} className="text-neutral-500" />
            <input
              className="w-full bg-transparent text-sm outline-none"
              value={searchInput.query}
              onChange={(event) => updateInput("query", event.target.value)}
              aria-label="Search career market"
              placeholder="Search a role, skill, company, or technology"
            />
          </label>
          <select
            className="h-11 rounded-xl border border-line bg-white/80 px-3 text-sm outline-none focus:border-neutral-500"
            value={searchInput.remote}
            onChange={(event) => updateInput("remote", event.target.value as SearchInput["remote"])}
            aria-label="Work arrangement filter"
          >
            <option value="any">All jobs</option>
            <option value="true">Remote only</option>
            <option value="false">On-site only</option>
          </select>
          <button
            type="submit"
            className="flex h-11 items-center justify-center gap-2 rounded-xl bg-ink px-4 text-sm font-medium text-white shadow-sm disabled:cursor-not-allowed disabled:opacity-60"
            disabled={loading}
            data-testid="career-map-submit"
          >
            {loading ? <RefreshCw size={16} className="animate-spin" /> : <Target size={16} />}
            Map
          </button>
        </form>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-neutral-600">
          {payload ? (
            <span>
              {payload.total} matching jobs for{" "}
              <strong className="font-semibold text-ink">{payload.correctedQuery || payload.query}</strong>
            </span>
          ) : (
            <span>Map the skills that show up across matching job postings.</span>
          )}
          {payload && payload.query !== payload.correctedQuery ? (
            <span className="rounded-md border border-line px-2 py-1 text-xs">
              corrected from {payload.query}
            </span>
          ) : null}
          {payload ? (
            <span className="rounded-md border border-line px-2 py-1 text-xs">
              {payload.jobs.length} jobs analyzed
            </span>
          ) : null}
          {selectedSkills.length ? (
            <span className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs text-emerald-800">
              {selectedSkills.length} selected
            </span>
          ) : null}
        </div>
      </section>

      <section className="grid min-h-0 flex-1 gap-4 overflow-hidden p-4 grid-cols-1 lg:grid-cols-[minmax(320px,0.9fr)_minmax(500px,1.3fr)_minmax(280px,0.78fr)]">
        <section className="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-white/80 bg-white/65 shadow-sm backdrop-blur">
          <PanelHeader
            icon={<BriefcaseBusiness size={17} />}
            title="Matching Jobs"
            detail={
              payload
                ? selectedSkills.length
                  ? `${filteredJobs.length} jobs match ${selectedSkills.join(", ")}`
                  : `${payload.jobs.length} jobs analyzed from ${payload.total} matches`
                : "Search results"
            }
          />
          <div className="min-h-0 flex-1 overflow-y-auto p-4">
            {error ? <StatusMessage title="Search failed" body={error} /> : null}
            {loading ? <StatusMessage title="Mapping market" body="Fetching jobs and skill counts." /> : null}
            {!loading && !error && payload?.jobs.length === 0 ? (
              <StatusMessage
                title="No jobs returned"
                body="Try a broader role or load the local demo dataset."
              />
            ) : null}
            {!loading && !error && payload && payload.jobs.length > 0 && filteredJobs.length === 0 ? (
              <StatusMessage
                title="No jobs match selected skills"
                body="Remove a selected skill or choose another skill from the map."
              />
            ) : null}
            {!loading && !error && !payload ? (
              <StatusMessage title="Start with a market" body="Try backend engineer, cloud, React, Java, Python, SQL, or AWS." />
            ) : null}
            <div className="space-y-3">
              {filteredJobs.map((job) => (
                <JobCard
                  key={job.id}
                  job={job}
                  selected={selectedJob?.id === job.id}
                  onClick={() => setSelectedJobId(job.id)}
                />
              ))}
            </div>
          </div>
        </section>

        <section className="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-white/80 bg-white/55 shadow-sm backdrop-blur">
          <PanelHeader
            icon={<Network size={17} />}
            title="Market Map"
            detail={payload ? "Click a skill to select it" : "Skill graph"}
          />
          <div className="min-h-0 flex-1">
            <SkillMap
              query={payload?.correctedQuery || searchInput.query}
              marketSkills={payload?.marketSkills ?? []}
              graph={payload?.graph ?? { nodes: [], edges: [] }}
              selectedSkills={selectedSkills}
              loading={loading}
              onToggleSelected={toggleSelectedSkill}
            />
          </div>
        </section>

        <aside className="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-white/80 bg-white/65 shadow-sm backdrop-blur">
          <PanelHeader
            icon={<Target size={17} />}
            title="Skill Details"
            detail={selectedSkills.length ? selectedSkills.join(", ") : "Select a skill"}
          />
          <div className="min-h-0 flex-1 overflow-y-auto p-4">
            <SelectedSkillsSection selectedSkills={selectedSkills} onRemove={toggleSelectedSkill} />
            <RecommendationsSection
              recommendations={payload?.recommendedSkills ?? []}
              selectedSkills={selectedSkills}
              maxRelatedJobCount={maxRelatedJobCount}
              onSelect={toggleSelectedSkill}
            />
          </div>
        </aside>
      </section>
    </main>
  );
}

function PanelHeader({
  icon,
  title,
  detail
}: {
  icon: ReactNode;
  title: string;
  detail: string;
}) {
  return (
    <div className="flex shrink-0 items-center justify-between gap-4 border-b border-white/70 bg-white/50 px-4 py-3 backdrop-blur">
      <div className="flex items-center gap-2">
        <span className="text-neutral-600">{icon}</span>
        <h2 className="font-semibold">{title}</h2>
      </div>
      <div className="truncate text-sm text-neutral-500">{detail}</div>
    </div>
  );
}

function SelectedSkillsSection({
  selectedSkills,
  onRemove
}: {
  selectedSkills: string[];
  onRemove: (skillName: string) => void;
}) {
  return (
    <section className="border-b border-line pb-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold">Selected Skills</h3>
      </div>
      {selectedSkills.length ? (
        <div className="flex flex-wrap gap-2">
          {selectedSkills.map((skill) => (
            <button
              key={skill}
              className="flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50/80 px-2 py-1 text-xs font-medium text-emerald-800"
              onClick={() => onRemove(skill)}
            >
              {skill}
              <X size={12} />
            </button>
          ))}
        </div>
      ) : (
        <p className="text-sm leading-5 text-neutral-600">No skill selected.</p>
      )}
    </section>
  );
}

function RecommendationsSection({
  recommendations,
  selectedSkills,
  maxRelatedJobCount,
  onSelect
}: {
  recommendations: RecommendedSkill[];
  selectedSkills: string[];
  maxRelatedJobCount: number;
  onSelect: (skillName: string) => void;
}) {
  const visibleRecommendations = recommendations.slice(0, 6);
  const selectedKeys = useMemo(() => new Set(selectedSkills.map((skill) => normalizeSkillKey(skill))), [selectedSkills]);
  return (
    <section className="py-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold">Related Skills</h3>
      </div>
      {visibleRecommendations.length ? (
        <div className="space-y-2">
          {visibleRecommendations.map((skill) => (
            <button
              key={skill.name}
              className={`w-full rounded-xl border p-3 text-left shadow-sm transition-colors ${
                selectedKeys.has(normalizeSkillKey(skill.name)) ? "border-emerald-300 bg-emerald-50/90" : "border-white/80 bg-white/70 hover:border-neutral-400"
              }`}
              onClick={() => onSelect(skill.name)}
            >
              <div className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-1.5 font-medium">
                  {selectedKeys.has(normalizeSkillKey(skill.name)) ? <Check size={13} /> : null}
                  {skill.name}
                </span>
                <span className="text-sm text-neutral-600">{skill.count} jobs</span>
              </div>
              <div className="mt-2 h-1.5 rounded bg-neutral-100">
                <div
                  className="h-1.5 rounded bg-skill"
                  style={{ width: `${Math.max(8, Math.round((skill.count / maxRelatedJobCount) * 100))}%` }}
                />
              </div>
            </button>
          ))}
        </div>
      ) : (
        <p className="text-sm leading-5 text-neutral-600">Related skills appear after SkillScan finds matching jobs.</p>
      )}
    </section>
  );
}

function JobCard({
  job,
  selected,
  onClick
}: {
  job: JobResult;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <article
      className={`relative rounded-xl border bg-white/78 shadow-sm backdrop-blur transition-colors ${
        selected ? "border-skill ring-2 ring-emerald-100" : "border-white/80 hover:border-neutral-400"
      }`}
    >
      {job.postingUrl ? (
        <a
          className="absolute right-3 top-3 flex h-8 w-8 items-center justify-center rounded-lg border border-white/80 bg-white/80 text-neutral-600 hover:border-neutral-400 hover:text-ink"
          href={job.postingUrl}
          target="_blank"
          rel="noreferrer"
          aria-label={`Open posting for ${job.title}`}
          title="Open posting"
        >
          <ExternalLink size={15} />
        </a>
      ) : null}
      <button onClick={onClick} className="w-full p-4 pr-14 text-left">
        <div className="font-semibold leading-5">{job.title}</div>
        <div className="mt-1 text-sm text-neutral-600">
          {job.company} - {job.location || "Location unavailable"}
        </div>
        <p className="mt-3 text-sm leading-5 text-neutral-700">{job.descriptionSnippet}</p>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {job.skills.slice(0, 5).map((skill) => (
            <span key={skill.name} className="rounded border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs text-emerald-800">
              {skill.name}
            </span>
          ))}
        </div>
      </button>
    </article>
  );
}

function SkillMap({
  query,
  marketSkills,
  graph,
  selectedSkills,
  loading,
  onToggleSelected
}: {
  query: string;
  marketSkills: MarketSkill[];
  graph: CareerMapPayload["graph"];
  selectedSkills: string[];
  loading: boolean;
  onToggleSelected: (skillName: string) => void;
}) {
  const positionedNodes = useMemo(() => positionNodes(graph.nodes), [graph.nodes]);
  const selectedKeys = useMemo(() => new Set(selectedSkills.map((skill) => normalizeSkillKey(skill))), [selectedSkills]);

  if (loading && !marketSkills.length) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center text-sm text-neutral-600">
        Building the market map.
      </div>
    );
  }

  if (!marketSkills.length) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center text-sm text-neutral-600">
        Search results with normalized skills appear here.
      </div>
    );
  }

  return (
    <div className="relative h-full min-h-[540px] overflow-hidden bg-[linear-gradient(180deg,rgba(255,255,255,0.72),rgba(247,251,247,0.42))]">
      <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        {positionedNodes.map((node) => {
          const isSelected = selectedKeys.has(normalizeSkillKey(node.label));
          return (
            <line
              key={`market-${node.id}`}
              x1="50"
              y1="50"
              x2={node.left}
              y2={node.top}
              stroke={isSelected ? "#0b8067" : "#c7d2c7"}
              strokeWidth={isSelected ? 0.78 : 0.34}
            />
          );
        })}
      </svg>

      <div className="absolute left-1/2 top-1/2 z-10 w-[164px] -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-white/90 bg-white/80 p-4 text-center shadow-md backdrop-blur">
        <div className="text-xs text-neutral-500">Market</div>
        <div className="mt-1 truncate text-sm font-semibold">{query || "Search"}</div>
      </div>

      {positionedNodes.map((node) => {
        const isSelected = selectedKeys.has(normalizeSkillKey(node.label));
        return (
          <button
            key={node.id}
            className={`absolute z-10 w-[132px] -translate-x-1/2 -translate-y-1/2 rounded-xl border bg-white/80 px-3 py-2 text-left text-sm shadow-sm backdrop-blur transition-colors ${
              isSelected
                ? "border-emerald-300 bg-emerald-50/95 text-emerald-900 ring-2 ring-emerald-100"
                : "border-white/80 hover:border-neutral-400"
            }`}
            style={{ left: `${node.left}%`, top: `${node.top}%` }}
            onClick={() => onToggleSelected(node.label)}
            data-testid={`skill-node-${slugSkill(node.label)}`}
          >
            <span className="flex items-center gap-1.5 font-medium">
              {isSelected ? <Check size={13} /> : null}
              <span className="truncate">{node.label}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

function positionNodes(nodes: GraphNode[]): PositionedNode[] {
  if (!nodes.length) {
    return [];
  }

  const visibleNodes = nodes.slice(0, 8);
  const radiusX = 35;
  const radiusY = 30;
  return visibleNodes.map((node, index) => {
    const angle = -Math.PI / 2 + (index / visibleNodes.length) * Math.PI * 2;
    return {
      ...node,
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

function sameSkill(left: string, right: string) {
  return normalizeSkillKey(left) === normalizeSkillKey(right);
}

function jobsMatchingSkills(jobs: JobResult[], skills: string[]) {
  const selectedKeys = skills.map((skill) => normalizeSkillKey(skill));
  if (!selectedKeys.length) {
    return jobs;
  }
  return jobs.filter((job) => {
    const jobSkillKeys = new Set(job.skills.map((skill) => normalizeSkillKey(skill.name)));
    return selectedKeys.every((skill) => jobSkillKeys.has(skill));
  });
}

function normalizeSkillKey(skill: string) {
  return skill.trim().toLowerCase();
}

function slugSkill(skill: string) {
  return normalizeSkillKey(skill).replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}
