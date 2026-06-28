// Central place for environment-driven config.
// Toggle NEXT_PUBLIC_USE_MOCK=false in .env.local once P2's FastAPI backend is live.

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK !== 'false';

export const DOMAIN = 'Data Structures & Algorithms';

export const DUNGEON_ID = 'dsa-dungeon-01';

// Simulated network latency for mock mode, so loading states are visible
// and feel honest to what the real LLM-backed endpoints will feel like.
export const MOCK_LATENCY = {
  fast: 250,
  question: 1400, // mimics LLM question-gen latency
  judge: 900, // mimics NLP judge + possible LLM fallback
};
