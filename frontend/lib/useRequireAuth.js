'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/useAuthStore';

/** Redirects to /login once the initial /auth/me check resolves and finds no session. */
export function useRequireAuth() {
  const router = useRouter();
  const { isAuthenticated, loading } = useAuthStore();

  useEffect(() => {
    if (!loading && !isAuthenticated) router.replace('/login');
  }, [loading, isAuthenticated, router]);

  return { ready: !loading && isAuthenticated, loading };
}
