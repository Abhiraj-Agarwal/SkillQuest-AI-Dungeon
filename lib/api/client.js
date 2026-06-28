// THE single file for all backend communication. No component, hook, or
// store should ever call fetch() directly — that's the rule from the team
// spec, and it's what makes "swap mock for live" a one-line change here
// instead of a hunt across every page.
//
// Toggle via NEXT_PUBLIC_USE_MOCK in .env.local — see lib/config.js.

import { API_BASE_URL, USE_MOCK } from '../config';
import * as mock from '../mock/mockData';

async function request(path, { method = 'GET', body, headers } = {}) {
  let res;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method,
      credentials: 'include', // sends the httpOnly JWT cookie P2 sets on login
      headers: { 'Content-Type': 'application/json', ...headers },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (networkErr) {
    const err = new Error('Could not reach the backend. Is it running?');
    err.code = 0;
    err.cause = networkErr;
    throw err;
  }

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const err = new Error(data?.error || `Request failed (${res.status})`);
    err.code = data?.code ?? res.status;
    throw err;
  }
  return data;
}

// ---------------- auth ----------------
export const auth = {
  register: (username, password) =>
    USE_MOCK
      ? mock.register(username, password)
      : request('/auth/register', { method: 'POST', body: { username, password } }),

  login: (username, password) =>
    USE_MOCK
      ? mock.login(username, password)
      : request('/auth/login', { method: 'POST', body: { username, password } }),

  logout: () => (USE_MOCK ? mock.logout() : request('/auth/logout', { method: 'POST' })),

  me: () => (USE_MOCK ? mock.me() : request('/auth/me')),
};

// ---------------- game ----------------
export const game = {
  getDungeon: (dungeonId) =>
    USE_MOCK ? mock.getDungeon(dungeonId) : request(`/game/dungeon/${dungeonId}`),

  enterRoom: (topic) =>
    USE_MOCK ? mock.enterRoom(topic) : request('/game/room/enter', { method: 'POST', body: { topic } }),

  submitAnswer: (payload) =>
    USE_MOCK ? mock.submitAnswer(payload) : request('/game/answer/submit', { method: 'POST', body: payload }),

  getPlayer: (playerId) =>
    USE_MOCK ? mock.getPlayer(playerId) : request(`/game/player/${playerId}`),

  joinGuildRaid: (guildId) =>
    USE_MOCK
      ? mock.joinGuildRaid(guildId)
      : request('/game/guild/raid/join', { method: 'POST', body: { guild_id: guildId } }),

  getLeaderboard: () => (USE_MOCK ? mock.getLeaderboard() : request('/game/leaderboard')),

  // Mock-mode-only convenience — see lib/mock/mockData.js respawn(). Once
  // real backend HP/death rules exist, point this at whatever P2 builds
  // (or remove if the backend handles respawn implicitly).
  respawn: () => (USE_MOCK ? mock.respawn() : Promise.resolve({ ok: true })),
};

// ---------------- ai (judge dashboard only — all other /ai/* routes are
// called server-to-server by P2, never directly by the frontend) ----------------
export const ai = {
  getDashboard: (playerId) =>
    USE_MOCK ? mock.getDashboard(playerId) : request(`/ai/dashboard/${playerId}`),
};
