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
};

type PositionedNode = GraphNode & {
  left: number;
  top: number;
  pathStartX: number;
  pathStartY: number;
  pathEndX: number;
  pathEndY: number;
};

const defaultSearch: SearchInput = {
  query: ""
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
              remote: null,
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
    <main className="flex h-screen flex-col overflow-hidden bg-paper text-ink">
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-line bg-[#fbfaf7] px-6">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-md border border-line bg-[#f4f2ed] text-skill">
            <Network size={18} />
          </span>
          <div className="text-base font-semibold">SkillScan</div>
        </div>
        <div className="text-sm text-neutral-600">Skill market workbench</div>
      </header>

      <section className="shrink-0 border-b border-line bg-[#f7f5ef] px-6 py-4">
        <form onSubmit={handleSubmit} className="grid gap-2 border border-line bg-[#fbfaf7] p-2 lg:grid-cols-[minmax(360px,1fr)_108px]">
          <label className="flex h-10 items-center gap-3 rounded-md border border-transparent bg-white px-3 focus-within:border-neutral-400">
            <Search size={17} className="text-neutral-500" />
            <input
              className="w-full bg-transparent text-sm outline-none"
              value={searchInput.query}
              onChange={(event) => updateInput("query", event.target.value)}
              aria-label="Search career market"
              placeholder="Search a role, skill, company, or technology"
            />
          </label>
          <button
            type="submit"
            className="flex h-10 items-center justify-center gap-2 rounded-md bg-ink px-4 text-sm font-medium text-white outline-none focus-visible:ring-2 focus-visible:ring-neutral-300 disabled:cursor-not-allowed disabled:opacity-60"
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
            <span className="rounded border border-line bg-[#fbfaf7] px-2 py-1 text-xs">
              corrected from {payload.query}
            </span>
          ) : null}
          {payload ? (
            <span className="rounded border border-line bg-[#fbfaf7] px-2 py-1 text-xs">
              {payload.jobs.length} jobs analyzed
            </span>
          ) : null}
          {selectedSkills.length ? (
            <span className="rounded border border-selected/30 bg-selected/10 px-2 py-1 text-xs text-selected">
              {selectedSkills.length} selected
            </span>
          ) : null}
        </div>
      </section>

      <section className="grid min-h-0 min-w-0 flex-1 grid-cols-1 gap-px overflow-hidden bg-line p-px xl:grid-cols-[minmax(280px,0.78fr)_minmax(460px,1.4fr)_minmax(230px,0.64fr)]">
        <section className="flex min-h-0 min-w-0 flex-col overflow-hidden bg-[#fbfaf7]">
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

        <section className="flex min-h-0 min-w-0 flex-col overflow-hidden bg-[#f4f2ed]">
          <PanelHeader
            icon={<Network size={17} />}
            title="Market Map"
            detail={payload ? "Select skill" : "Skill graph"}
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

        <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden bg-[#fbfaf7]">
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
    <div className="flex h-12 shrink-0 items-center justify-between gap-4 border-b border-line bg-[#eee9df] px-4">
      <div className="flex min-w-0 items-center gap-2">
        <span className="text-neutral-700">{icon}</span>
        <h2 className="truncate font-semibold">{title}</h2>
      </div>
      <div className="truncate text-sm text-neutral-600">{detail}</div>
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
              className="flex items-center gap-1.5 rounded border border-selected/30 bg-selected/10 px-2 py-1 text-xs font-medium text-selected outline-none hover:border-selected focus-visible:ring-2 focus-visible:ring-selected/15"
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
              className={`w-full rounded-md border p-3 text-left outline-none transition-colors focus-visible:ring-2 focus-visible:ring-neutral-300 ${
                selectedKeys.has(normalizeSkillKey(skill.name))
                  ? "border-selected/40 bg-selected/10 text-selected"
                  : "border-line bg-white hover:border-neutral-500"
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
              <div className="mt-2 h-1.5 rounded-sm bg-[#e8e3d9]">
                <div
                  className="h-1.5 rounded-sm bg-skill"
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
      className={`relative rounded-md border bg-white transition-colors ${
        selected ? "border-selected/45 bg-[#fbfefd]" : "border-line hover:border-neutral-500"
      }`}
    >
      {job.postingUrl ? (
        <a
          className="absolute right-3 top-3 flex h-8 w-8 items-center justify-center rounded-md border border-line bg-[#fbfaf7] text-neutral-600 outline-none hover:border-neutral-500 hover:text-ink focus-visible:ring-2 focus-visible:ring-neutral-300"
          href={job.postingUrl}
          target="_blank"
          rel="noreferrer"
          aria-label={`Open posting for ${job.title}`}
          title="Open posting"
        >
          <ExternalLink size={15} />
        </a>
      ) : null}
      <button onClick={onClick} className="block w-full min-w-0 overflow-hidden p-4 pr-14 text-left outline-none focus-visible:ring-2 focus-visible:ring-selected/15">
        <div className="truncate font-semibold leading-5">{job.title}</div>
        <div className="mt-1 truncate text-sm text-neutral-600">
          {job.company} / {job.location || "Location unavailable"}
        </div>
        <p className="mt-3 max-w-full overflow-hidden break-words text-sm leading-5 text-neutral-700">{job.descriptionSnippet}</p>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {job.skills.slice(0, 5).map((skill) => (
            <span key={skill.name} className="rounded border border-line bg-[#f4f2ed] px-2 py-1 text-xs text-neutral-700">
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
    <div className="relative h-full min-h-[540px] overflow-hidden bg-[linear-gradient(#ded9cf_1px,transparent_1px),linear-gradient(90deg,#ded9cf_1px,transparent_1px)] bg-[size:44px_44px]">
      <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        {positionedNodes.map((node) => {
          const isSelected = selectedKeys.has(normalizeSkillKey(node.label));
          return (
            <line
              key={`market-${node.id}`}
              x1={node.pathStartX}
              y1={node.pathStartY}
              x2={node.pathEndX}
              y2={node.pathEndY}
              stroke={isSelected ? "#0f766e" : "#bdb5a8"}
              strokeLinecap="round"
              strokeWidth={isSelected ? 0.34 : 0.18}
            />
          );
        })}
      </svg>

      <div className="absolute left-1/2 top-1/2 z-10 w-[164px] -translate-x-1/2 -translate-y-1/2 rounded-md border border-line bg-[#fbfaf7] p-4 text-center">
        <div className="text-xs text-neutral-500">Market</div>
        <div className="mt-1 truncate text-sm font-semibold">{query || "Search"}</div>
      </div>

      {positionedNodes.map((node) => {
        const isSelected = selectedKeys.has(normalizeSkillKey(node.label));
        return (
          <button
            key={node.id}
            className={`absolute z-10 w-[148px] -translate-x-1/2 -translate-y-1/2 rounded-md border px-3 py-2 text-left text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-selected/15 ${
              isSelected
                ? "border-selected/45 bg-[#eef8f5] text-selected"
                : "border-line bg-[#fbfaf7] hover:border-neutral-500"
            }`}
            style={{ left: `${node.left}%`, top: `${node.top}%` }}
            onClick={() => onToggleSelected(node.label)}
            data-testid={`skill-node-${slugSkill(node.label)}`}
          >
            <span className="grid grid-cols-[14px_minmax(0,1fr)] items-center gap-2 font-medium">
              <span className="flex h-3.5 w-3.5 items-center justify-center text-selected">
                {isSelected ? <Check size={12} /> : null}
              </span>
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
  const radiusX = 31;
  const radiusY = 27;
  return visibleNodes.map((node, index) => {
    const angle = -Math.PI / 2 + (index / visibleNodes.length) * Math.PI * 2;
    const vectorX = Math.cos(angle);
    const vectorY = Math.sin(angle);
    const left = Math.round((50 + vectorX * radiusX) * 10) / 10;
    const top = Math.round((50 + vectorY * radiusY) * 10) / 10;
    const startOffset = 8.4;
    const endOffset = 8.8;
    const pathStartX = Math.round((50 + vectorX * startOffset) * 10) / 10;
    const pathStartY = Math.round((50 + vectorY * startOffset) * 10) / 10;
    const pathEndX = Math.round((left - vectorX * endOffset) * 10) / 10;
    const pathEndY = Math.round((top - vectorY * endOffset) * 10) / 10;
    return {
      ...node,
      left,
      top,
      pathStartX,
      pathStartY,
      pathEndX,
      pathEndY
    };
  });
}

function StatusMessage({ title, body }: { title: string; body: string }) {
  return (
    <div className="mb-3 rounded-md border border-line bg-[#fbfaf7] p-4">
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
