'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { auth } from '@/lib/api/client';

export const useAuthStore = create(
  persist(
    (set, get) => ({
      player: null,
      isAuthenticated: false,
      loading: true, // true until the initial player-session check resolves
      error: null,

      async fetchMe() {
        const isInitialLoad = !get().player;
        if (isInitialLoad) set({ loading: true });
        try {
          const { player } = await auth.me();
          set({ player, isAuthenticated: true, loading: false, error: null });
        } catch {
          set({ player: null, isAuthenticated: false, loading: false });
        }
      },

      async login(username) {
        set({ error: null });
        try {
          const { player } = await auth.login(username);
          set({ player, isAuthenticated: true });
          return true;
        } catch (e) {
          set({ error: e.message });
          return false;
        }
      },

      async register(username) {
        set({ error: null });
        try {
          const { player } = await auth.register(username);
          set({ player, isAuthenticated: true });
          return true;
        } catch (e) {
          set({ error: e.message });
          return false;
        }
      },

      async logout() {
        await auth.logout().catch(() => {});
        set({ player: null, isAuthenticated: false });
      },

      clearError() {
        set({ error: null });
      },

      // Client-side optimistic decrement — see TODO in useGameStore.revealHintLocally
      // about adding a server-authoritative hint-spend endpoint.
      spendHintToken() {
        const p = get().player;
        if (!p || p.hint_tokens <= 0) return;
        set({ player: { ...p, hint_tokens: p.hint_tokens - 1 } });
      },
    }),
    {
      name: 'codecrypt-auth',
      // Persist display data only; the API adapter revalidates the player on load.
      partialize: (s) => ({ player: s.player, isAuthenticated: s.isAuthenticated }),
    }
  )
);
