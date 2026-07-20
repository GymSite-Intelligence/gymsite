/**
 * Skills catalog — organized by pillars from
 * docs/reviews/agent-swarm-core-review.md "Gaps by Pillar"
 * plus P-000 extended categories (Design UX, Produtividade, extras).
 *
 * Source of truth for skill → agentRole → ROT step binding.
 * Cursor skill files live at .cursor/skills/<id>/SKILL.md
 * Agent skill files live at .agent/skills/<id>/SKILL.md
 */

import type { AgentRole } from './sla-defaults.ts';

/** Review pillars (agent-swarm-core-review.md) + P-000 extensions */
export const SKILL_CATEGORY_IDS = [
  'strategy-product',
  'architecture-design',
  'code-quality',
  'ops-readiness',
  'documentation',
  'design-ux',
  'productivity',
] as const;

export type SkillCategoryId = (typeof SKILL_CATEGORY_IDS)[number];

export type SkillRuntimeStatus =
  | 'rot-real'
  | 'rot-partial'
  | 'simulated'
  | 'cursor-only'
  | 'planned';

export interface SkillDefinition {
  id: string;
  /** Agent role that owns this skill (null = Cursor/tooling only) */
  agentRole: AgentRole | null;
  /** Enters project-review / ROT flow? */
  inRotFlow: boolean;
  /** ROT step 1–5 when inRotFlow */
  rotStep?: 1 | 2 | 3 | 4 | 5;
  /** How far backend implements it today */
  runtime: SkillRuntimeStatus;
  description: string;
}

export interface SkillCategory {
  id: SkillCategoryId;
  /** Matches review heading style */
  label: string;
  /** Exact pillar title from agent-swarm-core-review.md (when applicable) */
  reviewPillar: string | null;
  /** Primary agent for this pillar */
  primaryAgentRole: AgentRole | null;
  /** ROT step when this is a review pillar */
  rotStep: 1 | 2 | 3 | 4 | 5 | null;
  /** P-000 section number for extended categories */
  p000Section?: number;
  skills: SkillDefinition[];
}

/**
 * Categories ordered like the review: Strategy → Architecture → Code → Ops → Docs,
 * then P-000 Design + Produtividade.
 */
export const SKILL_CATEGORIES: SkillCategory[] = [
  {
    id: 'strategy-product',
    label: 'Strategy & Product',
    reviewPillar: 'Strategy & Product (`roadmap-update` + `metrics-review`)',
    primaryAgentRole: 'Product',
    rotStep: 1,
    p000Section: 2,
    skills: [
      {
        id: 'roadmap-update',
        agentRole: 'Product',
        inRotFlow: true,
        rotStep: 1,
        runtime: 'rot-partial',
        description: 'Now/Next/Later roadmap vs reality',
      },
      {
        id: 'metrics-review',
        agentRole: 'Product',
        inRotFlow: true,
        rotStep: 1,
        runtime: 'rot-partial',
        description: 'Scorecard + governance KPIs',
      },
      {
        id: 'brainstorm',
        agentRole: 'Product',
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'Sparring partner de ideias',
      },
      {
        id: 'competitive-brief',
        agentRole: 'Product',
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'Dossiê competitivo',
      },
      {
        id: 'sprint-planning',
        agentRole: 'Product',
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'Capacidade + backlog sprint',
      },
      {
        id: 'stakeholder-update',
        agentRole: 'Product',
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'Update por audiência',
      },
      {
        id: 'synthesize-research',
        agentRole: 'Product',
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'Insights de pesquisa (PM)',
      },
      {
        id: 'write-spec',
        agentRole: 'Product',
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'PRD / feature spec',
      },
    ],
  },
  {
    id: 'architecture-design',
    label: 'Architecture & Design',
    reviewPillar: 'Architecture & Design (`architecture` + `system-design`)',
    primaryAgentRole: 'Architecture',
    rotStep: 2,
    p000Section: 1,
    skills: [
      {
        id: 'architecture',
        agentRole: 'Architecture',
        inRotFlow: true,
        rotStep: 2,
        runtime: 'rot-partial',
        description: 'Cria ou avalia ADR',
      },
      {
        id: 'system-design',
        agentRole: 'Architecture',
        inRotFlow: true,
        rotStep: 2,
        runtime: 'rot-partial',
        description: 'Design de sistema com NFRs',
      },
      {
        id: 'mermaid',
        agentRole: 'Architecture',
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'Diagramas Mermaid',
      },
      {
        id: 'pretty-mermaid',
        agentRole: 'Architecture',
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'Mermaid com layout polido',
      },
    ],
  },
  {
    id: 'code-quality',
    label: 'Code & Quality',
    reviewPillar: 'Code & Quality (`code-review` + `test-and-qa`)',
    primaryAgentRole: 'QA',
    rotStep: 3,
    p000Section: 1,
    skills: [
      {
        id: 'code-review',
        agentRole: 'QA',
        inRotFlow: true,
        rotStep: 3,
        runtime: 'planned',
        description: 'Review segurança/performance/correção',
      },
      {
        id: 'test-and-qa',
        agentRole: 'QA',
        inRotFlow: true,
        rotStep: 3,
        runtime: 'rot-partial',
        description: 'Lint + testes (ROT passo Código)',
      },
      {
        id: 'debug',
        agentRole: 'QA',
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'Sessão reproduce→isolate→diagnose→fix',
      },
    ],
  },
  {
    id: 'ops-readiness',
    label: 'Ops Readiness',
    reviewPillar: 'Ops Readiness (`deploy-checklist` + `incident-response`)',
    primaryAgentRole: 'Ops',
    rotStep: 4,
    p000Section: 3,
    skills: [
      {
        id: 'deploy-checklist',
        agentRole: 'Ops',
        inRotFlow: true,
        rotStep: 4,
        runtime: 'rot-partial',
        description: 'Checklist pré-deploy + artifacts',
      },
      {
        id: 'incident-response',
        agentRole: 'Ops',
        inRotFlow: true,
        rotStep: 4,
        runtime: 'planned',
        description: 'Triage SEV + postmortem',
      },
      {
        id: 'runbook',
        agentRole: 'Ops',
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'Passos operacionais exatos',
      },
      {
        id: 'change-request',
        agentRole: 'Ops',
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'Change request + rollback',
      },
      {
        id: 'capacity-plan',
        agentRole: 'Ops',
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'Utilização e gaps',
      },
      {
        id: 'risk-assessment',
        agentRole: 'Ops',
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'Risk register',
      },
      {
        id: 'compliance-tracking',
        agentRole: 'Ops',
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'SOC2/ISO/GDPR readiness',
      },
      {
        id: 'process-doc',
        agentRole: 'Ops',
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'SOP + RACI',
      },
      {
        id: 'process-optimization',
        agentRole: 'Ops',
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'As-is → to-be',
      },
      {
        id: 'status-report',
        agentRole: 'Ops',
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'Status G/Y/R + KPIs',
      },
      {
        id: 'vendor-review',
        agentRole: 'Ops',
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'TCO + recomendação',
      },
    ],
  },
  {
    id: 'documentation',
    label: 'Documentation',
    reviewPillar: 'Documentation (`documentation`)',
    primaryAgentRole: 'Docs',
    rotStep: 5,
    p000Section: 1,
    skills: [
      {
        id: 'documentation',
        agentRole: 'Docs',
        inRotFlow: true,
        rotStep: 5,
        runtime: 'rot-partial',
        description: 'README, API docs, onboarding',
      },
      {
        id: 'standup',
        agentRole: 'Docs',
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'Yesterday/Today/Blockers',
      },
    ],
  },
  {
    id: 'design-ux',
    label: 'Design (UX)',
    reviewPillar: null,
    primaryAgentRole: 'Design',
    rotStep: null,
    p000Section: 4,
    skills: [
      {
        id: 'accessibility-review',
        agentRole: 'Design',
        inRotFlow: false,
        runtime: 'planned',
        description: 'WCAG 2.1 AA',
      },
      {
        id: 'design-critique',
        agentRole: 'Design',
        inRotFlow: false,
        runtime: 'planned',
        description: 'Usabilidade/hierarquia',
      },
      {
        id: 'design-handoff',
        agentRole: 'Design',
        inRotFlow: false,
        runtime: 'planned',
        description: 'Spec para eng',
      },
      {
        id: 'design-system',
        agentRole: 'Design',
        inRotFlow: false,
        runtime: 'planned',
        description: 'Audit/doc/extend DS',
      },
      {
        id: 'research-synthesis',
        agentRole: 'Design',
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'Temas UX (Design)',
      },
      {
        id: 'user-research',
        agentRole: 'Design',
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'Plano + guia entrevista',
      },
      {
        id: 'ux-copy',
        agentRole: 'Design',
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'Microcopy / erros / CTAs',
      },
    ],
  },
  {
    id: 'productivity',
    label: 'Produtividade',
    reviewPillar: null,
    primaryAgentRole: null,
    rotStep: null,
    p000Section: 5,
    skills: [
      {
        id: 'project-review',
        agentRole: 'Audit',
        inRotFlow: false,
        runtime: 'rot-partial',
        description: 'Orquestra fluxo 360° (ROT ≈ runtime)',
      },
      {
        id: 'memory-management',
        agentRole: null,
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'Decode jargão memory',
      },
      {
        id: 'start',
        agentRole: null,
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'Bootstrap produtividade',
      },
      {
        id: 'task-management',
        agentRole: null,
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'Manipula TASKS.md',
      },
      {
        id: 'update',
        agentRole: null,
        inRotFlow: false,
        runtime: 'cursor-only',
        description: 'Sync tasks + memory',
      },
    ],
  },
];

export function allSkills(): SkillDefinition[] {
  return SKILL_CATEGORIES.flatMap((c) => c.skills);
}

export function getSkill(id: string): SkillDefinition | undefined {
  return allSkills().find((s) => s.id === id);
}

export function getCategory(id: SkillCategoryId): SkillCategory | undefined {
  return SKILL_CATEGORIES.find((c) => c.id === id);
}

/** Skills owned by an agent role */
export function skillsForRole(role: string): SkillDefinition[] {
  const r = role.toLowerCase();
  return allSkills().filter((s) => s.agentRole?.toLowerCase() === r);
}

/** Comma-joined skill ids for a ROT step (matches governance card skillKey) */
export function skillKeyForRotStep(step: 1 | 2 | 3 | 4 | 5): string {
  return allSkills()
    .filter((s) => s.inRotFlow && s.rotStep === step)
    .map((s) => s.id)
    .join(',');
}

/** Review pillars only (5 categories that map to ROT) */
export function reviewPillarCategories(): SkillCategory[] {
  return SKILL_CATEGORIES.filter((c) => c.reviewPillar !== null && c.rotStep !== null);
}

/** Map agent role → skill ids for seed / UI */
export function skillIdsByAgentRole(): Record<string, string[]> {
  const map: Record<string, string[]> = {};
  for (const skill of allSkills()) {
    if (!skill.agentRole) continue;
    if (!map[skill.agentRole]) map[skill.agentRole] = [];
    map[skill.agentRole].push(skill.id);
  }
  return map;
}

export function catalogSummary() {
  return {
    source: {
      review: 'docs/reviews/agent-swarm-core-review.md',
      p000: '.agent/rules/P-000_REGRA_MESTRA_MUDANCA.md',
      agentSkills: '.agent/skills/<id>/SKILL.md',
      cursorSkills: '.cursor/skills/<id>/SKILL.md',
      catalog: '.agent/skills/catalog/skills-catalog.ts',
    },
    categories: SKILL_CATEGORIES.map((c) => ({
      id: c.id,
      label: c.label,
      reviewPillar: c.reviewPillar,
      primaryAgentRole: c.primaryAgentRole,
      rotStep: c.rotStep,
      skillCount: c.skills.length,
      skills: c.skills.map((s) => ({
        id: s.id,
        agentRole: s.agentRole,
        inRotFlow: s.inRotFlow,
        runtime: s.runtime,
      })),
    })),
    totals: {
      categories: SKILL_CATEGORIES.length,
      skills: allSkills().length,
      inRotFlow: allSkills().filter((s) => s.inRotFlow).length,
      byRuntime: allSkills().reduce(
        (acc, s) => {
          acc[s.runtime] = (acc[s.runtime] || 0) + 1;
          return acc;
        },
        {} as Record<string, number>,
      ),
    },
  };
}
