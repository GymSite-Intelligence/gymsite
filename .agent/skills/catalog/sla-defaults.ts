/**
 * Agent roles for skill → ROT binding (P-000 / agent-swarm catalog).
 * Domain GymSite skills (gymsite-backend, …) live under `.agent/skills/<id>/`
 * and are listed separately in README — not as AgentRole owners here.
 */

export const AGENT_ROLES = [
  'Product',
  'Architecture',
  'QA',
  'Ops',
  'Docs',
  'Audit',
  'Design',
] as const;

export type AgentRole = (typeof AGENT_ROLES)[number];
