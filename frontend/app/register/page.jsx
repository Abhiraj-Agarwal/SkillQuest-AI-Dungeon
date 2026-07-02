'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '@/store/useAuthStore';
import PixelPanel from '@/components/ui/PixelPanel';
import PixelInput from '@/components/ui/PixelInput';
import PixelButton from '@/components/ui/PixelButton';

export default function RegisterPage() {
  const router = useRouter();
  const { register, error, clearError } = useAuthStore();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [localError, setLocalError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    clearError();
    setLocalError(null);
    if (password !== confirm) {
      setLocalError('Passwords do not match.');
      return;
    }
    setSubmitting(true);
    const ok = await register(username, password);
    setSubmitting(false);
    if (ok) router.push('/dungeon');
  }

  return (
    <div className="flex justify-center pt-10">
      <PixelPanel variant="arcane" className="w-full max-w-sm">
        <h1 className="font-display text-sm text-arcane mb-6 text-center">CREATE A CHARACTER</h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <PixelInput
            id="username"
            label="USERNAME"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoComplete="username"
          />
          <PixelInput
            id="password"
            label="PASSWORD"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="new-password"
          />
          <PixelInput
            id="confirm"
            label="CONFIRM PASSWORD"
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
            autoComplete="new-password"
          />
          {(localError || error) && (
            <p className="font-body text-blood text-sm">{localError || error}</p>
          )}
          <PixelButton type="submit" variant="arcane" disabled={submitting} className="mt-2">
            {submitting ? 'FORGING…' : 'BEGIN'}
          </PixelButton>
        </form>
        <p className="font-body text-parchment-dim text-sm text-center mt-4">
          Already have a character?{' '}
          <Link href="/login" className="text-arcane underline">
            Log in
          </Link>
        </p>
      </PixelPanel>
    </div>
  );
}
