'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { auth } from '@/lib/api/client';

export const useAuthStore = create(
  persist(
    (set, get) => ({
      player: null,
      isAuthenticated: false,
      loading: true, // true until the initial /auth/me check resolves
      error: null,

      async fetchMe() {
        set({ loading: true });
        try {
          const { player } = await auth.me();
          set({ player, isAuthenticated: true, loading: false, error: null });
        } catch {
          set({ player: null, isAuthenticated: false, loading: false });
        }
      },

      async login(username, password) {
        set({ error: null });
        try {
          const { player } = await auth.login(username, password);
          set({ player, isAuthenticated: true });
          return true;
        } catch (e) {
          set({ error: e.message });
          return false;
        }
      },

      async register(username, password) {
        set({ error: null });
        try {
          const { player } = await auth.register(username, password);
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
      // Only persist display info, never tokens — real auth lives in the
      // backend's httpOnly cookie. This is just so a refresh doesn't flash
      // a logged-out UI before /auth/me resolves.
      partialize: (s) => ({ player: s.player, isAuthenticated: s.isAuthenticated }),
    }
  )
);
