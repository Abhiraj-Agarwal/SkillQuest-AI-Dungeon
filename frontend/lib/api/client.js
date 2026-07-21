// The single browser-to-backend boundary. Components and stores consume the
// stable frontend view models below and never depend on FastAPI wire shapes.

import { API_BASE_URL } from '../config';
import { TOPIC_GRAPH, TOPIC_LABELS } from '../statMap';

const SESSION_KEY = 'skillquest-api-session';

let live = {
  playerId: null,
  sessionId: null,
  dungeon: null,
  combat: null,
};

function hydrateLiveState() {
  if (typeof window === 'undefined') return;
  try {
    live = { ...live, ...JSON.parse(window.localStorage.getItem(SESSION_KEY) || '{}') };
  } catch {
    window.localStorage.removeItem(SESSION_KEY);
  }
}

function persistLiveState() {
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(SESSION_KEY, JSON.stringify(live));
  }
}

function clearLiveState() {
  live = { playerId: null, sessionId: null, dungeon: null, combat: null };
  if (typeof window !== 'undefined') window.localStorage.removeItem(SESSION_KEY);
}

hydrateLiveState();

async function request(path, { method = 'GET', body, headers } = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: { 'Content-Type': 'application/json', ...headers },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (cause) {
    const error = new Error('Could not reach the backend. Is it running?');
    error.code = 0;
    error.cause = cause;
    throw error;
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(data?.detail)
      ? data.detail.map((item) => item.msg).join(', ')
      : data?.detail;
    const error = new Error(data?.error || detail || `Request failed (${response.status})`);
    error.code = data?.code ?? response.status;
    throw error;
  }
  return data;
}

function rememberPlayer(player) {
  live.playerId = player.player_id;
  persistLiveState();
  return { player };
}

async function currentPlayer() {
  hydrateLiveState();
  if (!live.playerId) {
    const error = new Error('Not authenticated');
    error.code = 401;
    throw error;
  }
  return request(`/game/player/${live.playerId}`);
}

function accuracyMap(player) {
  return Object.fromEntries(
    (player.accuracy_history || []).map((entry) => [entry.topic, entry.recent_accuracy])
  );
}

function normalizeDungeon(dungeon, player) {
  const accuracies = accuracyMap(player);
  const rooms = dungeon.rooms.filter((room) => room.topic in TOPIC_GRAPH).map((room) => {
    const recentAccuracy = accuracies[room.topic] ?? 0;
    const prerequisites = TOPIC_GRAPH[room.topic] || [];
    const isUnlocked = prerequisites.every((topic) => (accuracies[topic] ?? 0) > 0.65);
    let status = 'unlocked';
    if (!isUnlocked) status = 'locked';
    else if (recentAccuracy > 0.8) status = 'mastered';
    else if (recentAccuracy > 0 && recentAccuracy < 0.5) status = 'weak';

    return {
      ...room,
      label: TOPIC_LABELS[room.topic] || room.topic,
      status,
      recent_accuracy: recentAccuracy,
      prerequisites,
    };
  });
  const candidates = rooms.filter((room) => room.status !== 'locked' && !room.is_boss);
  const nextRoom = candidates.sort((a, b) => a.recent_accuracy - b.recent_accuracy)[0];

  return {
    dungeon_id: dungeon.dungeon_id,
    name: dungeon.name,
    domain: dungeon.domain,
    rooms,
    next_topic: nextRoom?.topic ?? null,
    boss_unlocked: Object.keys(TOPIC_GRAPH).every(
      (topic) => (accuracies[topic] ?? 0) > 0.65
    ),
  };
}

async function startDungeonSession(requestedDungeonId) {
  const player = await currentPlayer();
  let dungeon;
  try {
    dungeon = await request(`/game/dungeon/${requestedDungeonId}`);
  } catch (error) {
    if (error.code !== 404) throw error;
    const available = await request('/game/dungeons');
    if (!available.length) throw new Error('No dungeon has been seeded.');
    dungeon = await request(`/game/dungeon/${available[0].dungeon_id}`);
  }

  const session = await request('/game/session/start', {
    method: 'POST',
    body: { player_id: player.player_id, dungeon_id: dungeon.dungeon_id },
  });
  live.sessionId = session.session_id;
  live.dungeon = dungeon;
  persistLiveState();
  return normalizeDungeon(dungeon, player);
}

export const auth = {
  register: (username) =>
    request('/game/player/create', { method: 'POST', body: { username } }).then(rememberPlayer),

  login: (username) =>
    request(`/game/player/by-username/${encodeURIComponent(username)}`).then(rememberPlayer),

  logout: async () => {
    clearLiveState();
    return { ok: true };
  },

  me: async () => rememberPlayer(await currentPlayer()),
};

export const game = {
  getDungeon: (dungeonId) => startDungeonSession(dungeonId),

  enterRoom: async (topic) => {
    hydrateLiveState();
    if (!live.sessionId || !live.dungeon) await startDungeonSession('');
    const room =
      topic === 'boss'
        ? live.dungeon.rooms.find((candidate) => candidate.is_boss)
        : live.dungeon.rooms.find((candidate) => candidate.topic === topic);
    if (!room) throw new Error(`No room exists for ${topic}.`);

    const response = await request('/game/room/enter', {
      method: 'POST',
      body: { session_id: live.sessionId, room_id: room.room_id },
    });
    const continuing = live.combat?.roomId === room.room_id && live.combat.enemyHp > 0;
    const enemyHp = continuing ? live.combat.enemyHp : response.enemy_hp;
    live.combat = {
      roomId: room.room_id,
      topic,
      enemyHp,
      enemyHpMax: continuing ? live.combat.enemyHpMax : response.enemy_hp,
      playerHp: live.combat?.playerHp ?? 100,
    };
    persistLiveState();
    return {
      ...response.question,
      enemy_hp: enemyHp,
      enemy_hp_max: live.combat.enemyHpMax,
      enemy_name: topic === 'boss' ? 'The Big-O Devourer' : `${TOPIC_LABELS[topic] || topic} Wraith`,
    };
  },

  submitAnswer: async (payload) => {
    const player = await currentPlayer();
    const result = await request('/game/answer/submit', {
      method: 'POST',
      body: { ...payload, player_id: player.player_id },
    });
    const damageTaken = result.verdict === 'incorrect' ? 18 : result.verdict === 'partial' ? 8 : 0;
    live.combat = live.combat || { enemyHp: 0, enemyHpMax: 0, playerHp: 100 };
    live.combat.enemyHp = Math.max(0, live.combat.enemyHp - result.damage_dealt);
    live.combat.playerHp = Math.max(0, live.combat.playerHp - damageTaken);
    persistLiveState();
    return {
      ...result,
      player_hp_after: live.combat.playerHp,
      enemy_hp_after: live.combat.enemyHp,
    };
  },

  getPlayer: async (playerId) => {
    const player = await request(`/game/player/${playerId}`);
    return { ...player, topic_accuracies: accuracyMap(player) };
  },

  useHint: async (playerId, questionId) =>
    request('/game/hint/use', {
      method: 'POST',
      body: { player_id: playerId, question_id: questionId },
    }),

  joinGuildRaid: async (guildId) => {
    const player = await currentPlayer();
    let activeGuildId = guildId || player.guild_id;
    if (!activeGuildId) {
      const created = await request('/game/guild/create', {
        method: 'POST',
        body: { name: `${player.username}'s Guild`, creator_player_id: player.player_id },
      });
      activeGuildId = created.guild_id;
    }
    const joined = await request('/game/guild/raid/join', {
      method: 'POST',
      body: { guild_id: activeGuildId, player_id: player.player_id },
    });
    const [guild, status] = await Promise.all([
      request(`/game/guild/${activeGuildId}`),
      request(`/game/guild/raid/status?guild_id=${activeGuildId}`),
    ]);
    return {
      ...guild,
      raid_active: joined.raid_active,
      raid_boss_hp: Math.max(0, status.raid_boss_hp - status.raid_boss_damage),
      raid_boss_hp_max: status.raid_boss_hp,
      members: status.members.map((member) => ({
        ...member,
        topic: status.topic_assignments[member.player_id] || 'arrays',
      })),
    };
  },

  getLeaderboard: async () => ({ leaderboard: await request('/game/leaderboard') }),

  respawn: async () => {
    live.combat = null;
    persistLiveState();
    return { ok: true };
  },
};

export const ai = {
  getDashboard: async (playerId) => {
    const data = await request(`/ai/dashboard/${playerId}`);
    const nodes = Object.entries(TOPIC_GRAPH).map(([topic]) => ({
      id: topic,
      label: TOPIC_LABELS[topic] || topic,
      accuracy: data.topic_accuracies[topic] ?? 0,
      status: data.graph_state[topic] || 'locked',
    }));
    const edges = Object.entries(TOPIC_GRAPH).flatMap(([target, prerequisites]) =>
      prerequisites.map((source) => ({ source, target }))
    );
    return { ...data, graph: { nodes, edges } };
  },
};
