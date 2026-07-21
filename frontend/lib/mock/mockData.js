// Mock backend. Mirrors the real FastAPI contract field-for-field so that
// flipping NEXT_PUBLIC_USE_MOCK=false and pointing at the real API requires
// zero changes anywhere else in the app — only lib/api/client.js branches on it.
//
// State lives in memory (module scope) + localStorage for the logged-in user,
// so a page refresh during a demo doesn't lose progress. This is mock-only;
// the real backend owns the actual database.

import { MOCK_LATENCY, DUNGEON_ID, DOMAIN } from '../config';
import { TOPIC_GRAPH, TOPIC_LABELS } from '../statMap';
import { HEROES, DEFAULT_HERO_ID } from '../sprites/heroSprites';
import { monsterForTopic } from '../sprites/monsterSprites';

const POWERUP_MAX_USES_PER_WINDOW = 3;
const POWERUP_WINDOW_MS = 60 * 60 * 1000;

const STORAGE_KEY = 'codecrypt_mock_session';

const delay = (ms) => new Promise((res) => setTimeout(res, ms));

const TOPICS = Object.keys(TOPIC_GRAPH);

// ---- question bank (placeholder content — P3 replaces with live LLM calls) ----
const QUESTION_BANK = {
  arrays: {
    easy: { question: 'What is the time complexity of accessing an element by index in an array?', hint: 'Think about how memory addresses are calculated.' },
    medium: { question: 'How would you reverse an array in-place without extra memory?', hint: 'Two pointers, swap and converge.' },
    hard: { question: 'Explain how you would find the maximum subarray sum in O(n) time.', hint: "Kadane's algorithm tracks a running sum." },
  },
  linked_lists: {
    easy: { question: 'What is the main advantage of a linked list over an array?', hint: 'Think about insertion cost.' },
    medium: { question: 'How do you detect a cycle in a linked list?', hint: "Two runners, one fast, one slow." },
    hard: { question: 'How would you reverse a linked list in groups of k?', hint: 'Reverse each group, then relink boundaries.' },
  },
  stacks_queues: {
    easy: { question: 'What order does a stack process elements in?', hint: 'Last one in...' },
    medium: { question: 'How would you implement a queue using two stacks?', hint: 'One stack absorbs pushes, the other handles pops.' },
    hard: { question: 'How do you design a stack that also supports retrieving the minimum in O(1)?', hint: 'Carry a second stack of running minimums.' },
  },
  binary_search: {
    easy: { question: 'What precondition must hold for binary search to work?', hint: 'Order matters.' },
    medium: { question: 'How do you find the first occurrence of a target in a sorted array with duplicates?', hint: 'Bias the search left after a match.' },
    hard: { question: 'How would you binary search on a rotated sorted array?', hint: 'Figure out which half is properly sorted first.' },
  },
  recursion: {
    easy: { question: 'What two things does every correct recursive function need?', hint: 'Base case, and progress toward it.' },
    medium: { question: 'How would you generate all permutations of a string recursively?', hint: 'Fix one character, recurse on the rest.' },
    hard: { question: 'How does recursion depth relate to stack overflow risk, and how can tail recursion help?', hint: 'Each call frame costs stack space.' },
  },
  trees: {
    easy: { question: 'What distinguishes a binary tree from a general tree?', hint: 'Count the children.' },
    medium: { question: 'How do you compute the height of a binary tree recursively?', hint: '1 + max(left height, right height).' },
    hard: { question: 'How would you serialize and deserialize a binary tree?', hint: 'Preorder traversal with null markers.' },
  },
  binary_search_tree: {
    easy: { question: 'What property must every node in a BST satisfy?', hint: 'Left subtree, right subtree, ordering.' },
    medium: { question: 'How do you delete a node with two children from a BST?', hint: 'Replace with the in-order successor.' },
    hard: { question: 'How would you validate whether a binary tree is a valid BST?', hint: 'Track a valid (min, max) range per node.' },
  },
  heaps: {
    easy: { question: 'What is the time complexity of peeking the minimum in a min-heap?', hint: 'The root is always the answer.' },
    medium: { question: 'How do you build a heap from an unsorted array in-place?', hint: 'Heapify from the bottom up.' },
    hard: { question: 'How would you find the k-th largest element using a heap, and why is it efficient?', hint: 'A min-heap of size k tracks the top candidates.' },
  },
  graphs: {
    easy: { question: 'What is the difference between BFS and DFS traversal order?', hint: 'Queue versus stack.' },
    medium: { question: "How does Dijkstra's algorithm find shortest paths?", hint: 'Greedily expand the closest unvisited node.' },
    hard: { question: 'How would you detect a cycle in a directed graph?', hint: 'Track nodes currently on the recursion stack.' },
  },
  dynamic_programming: {
    easy: { question: 'What problem property makes dynamic programming applicable?', hint: 'Overlapping subproblems.' },
    medium: { question: 'How would you solve the 0/1 knapsack problem with DP?', hint: 'Table indexed by item and remaining capacity.' },
    hard: { question: 'How do you reconstruct the actual solution path from a DP table, not just the optimal value?', hint: 'Backtrack through the choices that led to each cell.' },
  },
  sorting_algorithms: {
    easy: { question: 'What is the average time complexity of merge sort?', hint: 'Divide and conquer halves the work each level.' },
    medium: { question: 'Why is quicksort worst-case O(n^2), and how do you avoid it?', hint: 'Bad pivot choices on already-sorted input.' },
    hard: { question: 'How would you sort an array of n integers in O(n) time if their range is bounded?', hint: 'Counting sort exploits the bounded range.' },
  },
};

// ---- module-level mutable state (mock "database") ----
let state = {
  player: null, // Player
  accuracy: {}, // topic -> AccuracyHistory
  difficultyHistory: [], // {topic, difficulty, timestamp}
  scoreHistory: [], // {score, verdict, timestamp}
  combat: null, // current in-flight question + enemy hp
};

function freshAccuracy() {
  const acc = {};
  TOPICS.forEach((t) => {
    acc[t] = { topic: t, attempts: 0, correct: 0, recent_accuracy: 0, last_5_results: [], mastered: false };
  });
  return acc;
}

function loadFromStorage() {
  if (typeof window === 'undefined') return;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) state = JSON.parse(raw);
  } catch {
    /* ignore corrupt storage */
  }
}

function saveToStorage() {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

loadFromStorage();

// Mirrors the backend's one-way `mastered` ratchet: a topic counts as
// proven once its recent_accuracy has EVER crossed the unlock threshold, so
// a later dip in the rolling last_5_results window can't re-lock a room the
// player already legitimately opened.
function isProven(topic) {
  const a = state.accuracy[topic];
  return Boolean(a?.mastered) || (a?.recent_accuracy ?? 0) > 0.65;
}

function statusForTopic(topic) {
  const prereqs = TOPIC_GRAPH[topic];
  const unlocked = prereqs.every((p) => isProven(p));
  if (!unlocked) return 'locked';
  const acc = state.accuracy[topic]?.recent_accuracy ?? 0;
  if (acc === 0) return 'unlocked';
  if (acc >= 0.9) return 'mastered';
  if (acc < 0.5) return 'weak';
  return 'unlocked';
}

function bossUnlocked() {
  // Matches the real backend: every topic must itself be proven (not just
  // reachable) before the boss door opens.
  return TOPICS.every((t) => isProven(t));
}

function buildDungeon() {
  const rooms = TOPICS.map((topic) => ({
    topic,
    label: TOPIC_LABELS[topic],
    status: statusForTopic(topic),
    recent_accuracy: state.accuracy[topic]?.recent_accuracy ?? 0,
    prerequisites: TOPIC_GRAPH[topic],
  }));
  const weak = rooms.filter((r) => r.status === 'weak' || r.recent_accuracy === 0);
  const next_topic = weak.length ? weak.sort((a, b) => a.recent_accuracy - b.recent_accuracy)[0].topic : null;
  return { dungeon_id: DUNGEON_ID, domain: DOMAIN, rooms, next_topic, boss_unlocked: bossUnlocked() };
}

function pickDifficulty(topic) {
  const acc = state.accuracy[topic]?.recent_accuracy ?? 0;
  if (acc > 0.8) return 'hard';
  if (acc > 0.5) return 'medium';
  return 'easy';
}

function requireAuth() {
  if (!state.player) {
    const err = new Error('Not authenticated');
    err.code = 401;
    throw err;
  }
}

// Read-only view of the cooldown window, mirroring backend/routes/game.py's
// _powerup_status -- does not reset an expired window (only usePowerup does).
function withPowerupStatus(player) {
  const windowStart = player.powerup_window_start ? new Date(player.powerup_window_start) : null;
  const windowActive = windowStart && Date.now() - windowStart.getTime() < POWERUP_WINDOW_MS;
  const uses = windowActive ? player.powerup_uses_this_window || 0 : 0;
  return {
    ...player,
    hero_id: player.hero_id || DEFAULT_HERO_ID,
    powerup_uses_remaining: Math.max(0, POWERUP_MAX_USES_PER_WINDOW - uses),
    powerup_resets_at: windowActive ? new Date(windowStart.getTime() + POWERUP_WINDOW_MS).toISOString() : null,
  };
}

// ---------------- public mock API (same shapes the real client.js expects) ----------------

export async function register(username) {
  await delay(MOCK_LATENCY.fast);
  if (!username) {
    const err = new Error('Character name required');
    err.code = 400;
    throw err;
  }
  state.player = {
    player_id: `mock-${username}`,
    username,
    level: 1,
    total_xp: 0,
    streak_days: 1,
    last_active: new Date().toISOString(),
    guild_id: null,
    hint_tokens: 3,
    hero_id: null,
    powerup_window_start: null,
    powerup_uses_this_window: 0,
  };
  state.accuracy = freshAccuracy();
  state.difficultyHistory = [];
  state.scoreHistory = [];
  saveToStorage();
  return { player: withPowerupStatus(state.player) };
}

export async function login(username) {
  await delay(MOCK_LATENCY.fast);
  if (!state.player || state.player.username !== username) {
    // mock mode: auto-provision so teammates can demo without a real DB
    return register(username);
  }
  return { player: withPowerupStatus(state.player) };
}

export async function logout() {
  await delay(MOCK_LATENCY.fast / 2);
  state.player = null;
  saveToStorage();
  return { ok: true };
}

export async function me() {
  await delay(MOCK_LATENCY.fast / 2);
  if (!state.player) {
    const err = new Error('Not authenticated');
    err.code = 401;
    throw err;
  }
  return { player: withPowerupStatus(state.player) };
}

export async function getDungeon(_dungeonId) {
  await delay(MOCK_LATENCY.fast);
  requireAuth();
  return buildDungeon();
}

export async function enterRoom(topic) {
  await delay(MOCK_LATENCY.question);
  requireAuth();

  const isBoss = topic === 'boss';
  if (isBoss && !bossUnlocked()) {
    const err = new Error('The boss door is sealed. Clear every other room first.');
    err.code = 403;
    throw err;
  }

  const difficulty = isBoss ? 'hard' : pickDifficulty(topic);
  let questionTopic = topic;
  if (isBoss) {
    questionTopic = TOPICS[Math.floor(Math.random() * TOPICS.length)];
  } else {
    state.difficultyHistory.unshift({ topic, difficulty, timestamp: new Date().toISOString() });
    state.difficultyHistory = state.difficultyHistory.slice(0, 10);
  }

  const bank = QUESTION_BANK[questionTopic] || QUESTION_BANK.arrays;
  const q = bank[difficulty];
  const question_id = `${topic}-${Date.now()}`;

  // Continuing the same fight (same room, enemy not yet defeated) keeps the
  // existing enemy HP so multiple questions chip away at one encounter.
  // Player HP persists across the whole dungeon run, not per-room.
  const continuingSameFight = state.combat && state.combat.topic === topic && state.combat.enemy_hp > 0;
  const freshEnemyMax = isBoss ? 300 : difficulty === 'hard' ? 120 : difficulty === 'medium' ? 90 : 60;

  state.combat = {
    question_id,
    topic,
    difficulty,
    enemy_hp: continuingSameFight ? state.combat.enemy_hp : freshEnemyMax,
    enemy_hp_max: continuingSameFight ? state.combat.enemy_hp_max : freshEnemyMax,
    player_hp: state.combat?.player_hp ?? 100,
    player_hp_max: 100,
  };
  saveToStorage();

  return {
    question_id,
    topic,
    difficulty,
    question: q.question,
    hint: q.hint,
    enemy_hp: state.combat.enemy_hp,
    enemy_hp_max: state.combat.enemy_hp_max,
    enemy_name: monsterForTopic(isBoss ? 'boss' : topic).name,
  };
}

// Mock-only "respawn" — clears the persisted combat state so the next
// enterRoom() call starts the player back at full HP. A real backend would
// likely just heal on a town/checkpoint visit; this is the dev-mode analog.
export async function respawn() {
  await delay(MOCK_LATENCY.fast / 2);
  state.combat = null;
  saveToStorage();
  return { ok: true };
}

export async function submitAnswer({ question_id, player_answer, response_time_ms }) {
  await delay(MOCK_LATENCY.judge);
  requireAuth();
  if (!state.combat || state.combat.question_id !== question_id) {
    const err = new Error('No active question for this submission');
    err.code = 409;
    throw err;
  }

  const trimmed = (player_answer || '').trim();
  let verdict;
  let score;
  if (trimmed.length === 0) {
    verdict = 'incorrect';
    score = 0;
  } else {
    // weighted random, biased toward correct for richer-than-empty answers
    const roll = Math.random();
    const lengthBonus = Math.min(trimmed.length / 200, 0.15);
    const adjusted = roll + lengthBonus;
    if (adjusted > 0.45) {
      verdict = 'correct';
      score = 0.65 + Math.random() * 0.35;
    } else if (adjusted > 0.2) {
      verdict = 'partial';
      score = 0.3 + Math.random() * 0.35;
    } else {
      verdict = 'incorrect';
      score = Math.random() * 0.3;
    }
  }

  // Consume a pending Titan's Smash/Valkyrie's Charge-style powerup first
  // (forces a correct critical hit outright), same as the real backend.
  if (state.player.pending_force_correct) {
    verdict = 'correct';
    score = Math.max(score, 0.9);
    state.player.pending_force_correct = false;
  } else if (state.player.pending_verdict_boost) {
    // Consume a pending Shadow Step-style powerup, same as the real backend.
    verdict = { incorrect: 'partial', partial: 'correct' }[verdict] || verdict;
    state.player.pending_verdict_boost = false;
  }

  // slow responses (>12s) take a small extra hit, matching the README rule
  const slowPenalty = response_time_ms > 12000 ? 0.5 : 1;

  const damage_multiplier = verdict === 'correct' ? 2.0 : verdict === 'partial' ? 1.0 : 0.0;
  const baseDamage = 25;
  const damageDealt = Math.round(baseDamage * damage_multiplier * slowPenalty);
  const damageTaken = verdict === 'correct' ? 0 : verdict === 'partial' ? 8 : 18;

  state.combat.enemy_hp = Math.max(0, state.combat.enemy_hp - damageDealt);
  state.combat.player_hp = Math.max(0, state.combat.player_hp - damageTaken);

  let xp_gained = verdict === 'correct' ? 30 : verdict === 'partial' ? 12 : 2;

  // Consume a pending Arcane Surge-style powerup, same as the real backend.
  if (state.player.pending_xp_multiplier && state.player.pending_xp_multiplier !== 1.0) {
    xp_gained = Math.round(xp_gained * state.player.pending_xp_multiplier);
    state.player.pending_xp_multiplier = 1.0;
  }

  const topic = state.combat.topic;
  const acc = state.accuracy[topic];
  if (acc) {
    acc.attempts += 1;
    if (verdict === 'correct') acc.correct += 1;
    acc.last_5_results = [...acc.last_5_results, verdict === 'correct'].slice(-5);
    acc.recent_accuracy =
      acc.last_5_results.filter(Boolean).length / Math.max(acc.last_5_results.length, 1);
    if (acc.recent_accuracy > 0.65) acc.mastered = true;
  }

  state.scoreHistory.unshift({ score: Number(score.toFixed(2)), verdict, timestamp: new Date().toISOString() });
  state.scoreHistory = state.scoreHistory.slice(0, 10);

  state.player.total_xp += xp_gained;
  state.player.level = 1 + Math.floor(state.player.total_xp / 150);

  const feedback =
    verdict === 'correct'
      ? 'Correct! That lands clean.'
      : verdict === 'partial'
      ? 'Partially correct — you have the idea but missed detail.'
      : 'Not quite. Review this topic and try again.';

  saveToStorage();

  return {
    verdict,
    score: Number(score.toFixed(2)),
    damage_multiplier,
    damage_dealt: damageDealt,
    feedback,
    xp_gained,
    player_hp_after: state.combat.player_hp,
    enemy_hp_after: state.combat.enemy_hp,
    // Mock combat is purely HP-based (no server-side correct-answer counting),
    // so the room/dungeon "cleared" signal is just the enemy's HP hitting 0 --
    // mirrors the shape of the real backend's response so callers that check
    // these fields (see app/combat, app/boss) behave the same in both modes.
    room_cleared: state.combat.enemy_hp <= 0,
    dungeon_completed: false,
  };
}

export async function getPlayer(_playerId) {
  await delay(MOCK_LATENCY.fast);
  requireAuth();
  const topic_accuracies = {};
  TOPICS.forEach((t) => {
    topic_accuracies[t] = state.accuracy[t]?.recent_accuracy ?? 0;
  });
  // Mirrors the real backend's accuracy_history shape (attempts/correct per
  // topic) -- the profile page sums these for a total questions-solved count.
  const accuracy_history = TOPICS.map((t) => ({
    topic: t,
    attempts: state.accuracy[t]?.attempts ?? 0,
    correct: state.accuracy[t]?.correct ?? 0,
    recent_accuracy: state.accuracy[t]?.recent_accuracy ?? 0,
    mastered: state.accuracy[t]?.mastered ?? false,
  }));
  return { ...withPowerupStatus(state.player), topic_accuracies, accuracy_history };
}

export async function setHero(_playerId, heroId) {
  await delay(MOCK_LATENCY.fast / 2);
  requireAuth();
  if (!HEROES[heroId]) {
    const err = new Error(`Unknown hero: ${heroId}`);
    err.code = 422;
    throw err;
  }
  state.player.hero_id = heroId;
  saveToStorage();
  return { hero_id: heroId };
}

export async function usePowerup(_playerId, questionId) {
  await delay(MOCK_LATENCY.fast / 2);
  requireAuth();
  const hero = HEROES[state.player.hero_id] || HEROES[DEFAULT_HERO_ID];

  const windowStart = state.player.powerup_window_start ? new Date(state.player.powerup_window_start) : null;
  const windowExpired = !windowStart || Date.now() - windowStart.getTime() >= POWERUP_WINDOW_MS;
  if (windowExpired) {
    state.player.powerup_window_start = new Date().toISOString();
    state.player.powerup_uses_this_window = 0;
  }

  if (state.player.powerup_uses_this_window >= POWERUP_MAX_USES_PER_WINDOW) {
    const resetsAt = new Date(new Date(state.player.powerup_window_start).getTime() + POWERUP_WINDOW_MS);
    const err = new Error(`${hero.powerupName} is on cooldown until ${resetsAt.toLocaleTimeString()}.`);
    err.code = 429;
    throw err;
  }

  const response = { hero_id: state.player.hero_id || DEFAULT_HERO_ID, powerup_name: hero.powerupName, effect: hero.effect };

  if (hero.effect === 'force_correct') {
    state.player.pending_force_correct = true;
    response.queued = true;
  } else if (hero.effect === 'force_correct_heal') {
    state.player.pending_force_correct = true;
    response.queued = true;
    response.heal_to_full = true;
    if (state.combat) state.combat.player_hp = state.combat.player_hp_max;
  } else if (hero.effect === 'double_xp_next') {
    state.player.pending_xp_multiplier = 2.0;
  } else if (hero.effect === 'verdict_boost_next') {
    state.player.pending_verdict_boost = true;
  } else if (hero.effect === 'free_hint_bonus_xp') {
    if (!state.combat || state.combat.question_id !== questionId) {
      const err = new Error('No active question for this powerup');
      err.code = 409;
      throw err;
    }
    const bank = QUESTION_BANK[state.combat.topic] || QUESTION_BANK.arrays;
    const q = bank[state.combat.difficulty];
    state.player.total_xp += hero.xp;
    state.player.level = 1 + Math.floor(state.player.total_xp / 150);
    response.hint_text = q.hint;
    response.xp_awarded = hero.xp;
  } else if (hero.effect === 'refill_hints') {
    state.player.hint_tokens = 3;
    response.hint_tokens = state.player.hint_tokens;
  }

  state.player.powerup_uses_this_window += 1;
  saveToStorage();

  response.powerup_uses_remaining = POWERUP_MAX_USES_PER_WINDOW - state.player.powerup_uses_this_window;
  response.powerup_resets_at = new Date(
    new Date(state.player.powerup_window_start).getTime() + POWERUP_WINDOW_MS
  ).toISOString();
  return response;
}

export async function useHint(_playerId, _questionId) {
  await delay(MOCK_LATENCY.fast / 2);
  requireAuth();
  if (state.player.hint_tokens <= 0) {
    const err = new Error('No hint tokens remaining');
    err.code = 400;
    throw err;
  }
  state.player.hint_tokens -= 1;
  saveToStorage();
  return { ok: true, hint_tokens: state.player.hint_tokens };
}

export async function joinGuildRaid(_guildId) {
  await delay(MOCK_LATENCY.fast);
  requireAuth();
  state.player.guild_id = state.player.guild_id || 'mock-guild-01';
  saveToStorage();
  return {
    guild_id: state.player.guild_id,
    name: 'The Stack Overflowers',
    members: [
      { player_id: state.player.player_id, username: state.player.username, topic: 'arrays' },
      { player_id: 'mock-ally-1', username: 'kavi_codes', topic: 'trees' },
      { player_id: 'mock-ally-2', username: 'priya_dev', topic: 'graphs' },
    ],
    raid_boss_hp: 240,
    raid_boss_hp_max: 400,
    raid_active: true,
  };
}

export async function getLeaderboard() {
  await delay(MOCK_LATENCY.fast);
  const me = state.player;
  const board = [
    { player_id: 'mock-ally-1', username: 'kavi_codes', total_xp: 980, streak_days: 6, level: 7, hero_id: 'titan_warrior' },
    { player_id: 'mock-ally-2', username: 'priya_dev', total_xp: 740, streak_days: 3, level: 5, hero_id: 'mindweave_mage' },
    { player_id: 'mock-ally-3', username: 'theo_b', total_xp: 510, streak_days: 9, level: 4, hero_id: 'shadow_rogue' },
    { player_id: 'mock-ally-4', username: 'sana_q', total_xp: 320, streak_days: 1, level: 3, hero_id: 'valkyrie_warrior' },
  ];
  if (me) {
    board.push({
      player_id: me.player_id,
      username: me.username,
      total_xp: me.total_xp,
      streak_days: me.streak_days,
      level: me.level,
      hero_id: me.hero_id,
    });
  }
  board.sort((a, b) => b.total_xp - a.total_xp);
  return { leaderboard: board };
}

export async function getDashboard(_playerId) {
  await delay(MOCK_LATENCY.fast);
  requireAuth();
  const dungeon = buildDungeon();
  const nodes = dungeon.rooms.map((r) => ({
    id: r.topic,
    label: r.label,
    accuracy: r.recent_accuracy,
    status: r.status,
  }));
  const edges = [];
  TOPICS.forEach((t) => {
    TOPIC_GRAPH[t].forEach((prereq) => edges.push({ source: prereq, target: t }));
  });
  const topic_accuracies = {};
  TOPICS.forEach((t) => {
    topic_accuracies[t] = state.accuracy[t]?.recent_accuracy ?? 0;
  });
  return {
    graph: { nodes, edges },
    difficulty_history: state.difficultyHistory,
    score_history: state.scoreHistory,
    topic_accuracies,
  };
}
