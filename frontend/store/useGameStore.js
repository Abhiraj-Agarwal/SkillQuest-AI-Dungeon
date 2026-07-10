'use client';

import { create } from 'zustand';
import { game } from '@/lib/api/client';

export const useGameStore = create((set, get) => ({
  dungeon: null,
  loadingDungeon: false,
  dungeonError: null,

  // active fight
  currentQuestion: null, // Question shape from lib/types.js
  combat: null, // { playerHp, playerHpMax, enemyHp, enemyHpMax, enemyName }
  enteringRoom: false,
  questionStartedAt: null,

  // last answer outcome, shown before returning to the map
  lastResult: null,
  submitting: false,
  submitError: null,

  hintRevealed: false,

  async loadDungeon(dungeonId) {
    set({ loadingDungeon: true, dungeonError: null });
    try {
      const dungeon = await game.getDungeon(dungeonId);
      set({ dungeon, loadingDungeon: false });
    } catch (e) {
      set({ dungeonError: e.message, loadingDungeon: false });
    }
  },

  async enterRoom(topic) {
    set({ enteringRoom: true, lastResult: null, hintRevealed: false, submitError: null });
    try {
      const q = await game.enterRoom(topic);
      set({
        currentQuestion: q,
        combat: {
          playerHp: get().combat?.playerHp ?? 100,
          playerHpMax: 100,
          enemyHp: q.enemy_hp,
          enemyHpMax: q.enemy_hp_max ?? q.enemy_hp,
          enemyName: q.enemy_name,
        },
        enteringRoom: false,
        questionStartedAt: Date.now(),
      });
    } catch (e) {
      set({ enteringRoom: false, dungeonError: e.message });
    }
  },

  async submitAnswer(answerText) {
    const { currentQuestion, questionStartedAt } = get();
    if (!currentQuestion) return null;
    set({ submitting: true, submitError: null });
    try {
      const response_time_ms = Date.now() - (questionStartedAt ?? Date.now());
      const result = await game.submitAnswer({
        question_id: currentQuestion.question_id,
        player_answer: answerText,
        response_time_ms,
      });
      set((s) => ({
        submitting: false,
        lastResult: result,
        combat: {
          ...s.combat,
          playerHp: result.player_hp_after,
          enemyHp: result.enemy_hp_after,
        },
      }));
      return result;
    } catch (e) {
      set({ submitting: false, submitError: e.message });
      return null;
    }
  },

  async revealHint(playerId, decrementFn) {
    const questionId = get().currentQuestion?.question_id;
    if (!questionId) return;
    try {
      await game.useHint(playerId, questionId);
      set({ hintRevealed: true, submitError: null });
      decrementFn?.();
    } catch (e) {
      set({ submitError: e.message });
    }
  },

  resetCombat() {
    set({ currentQuestion: null, combat: null, lastResult: null, hintRevealed: false });
  },

  async retreat() {
    await game.respawn().catch(() => {});
    get().resetCombat();
  },
}));
