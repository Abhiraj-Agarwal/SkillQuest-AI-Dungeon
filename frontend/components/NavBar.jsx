'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Menu, X, Sword, ScrollText, Users, Trophy, BrainCircuit } from 'lucide-react';
import clsx from 'clsx';
import { useAuthStore } from '@/store/useAuthStore';

const LINKS = [
  { href: '/dungeon', label: 'Dungeon', icon: Sword },
  { href: '/stats', label: 'Stats', icon: ScrollText },
  { href: '/guild', label: 'Guild', icon: Users },
  { href: '/leaderboard', label: 'Ranks', icon: Trophy },
  { href: '/dashboard', label: 'AI Core', icon: BrainCircuit },
];

export default function NavBar() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const { player, isAuthenticated, logout } = useAuthStore();

  if (!isAuthenticated) return null;

  async function handleLogout() {
    await logout();
    router.push('/login');
  }

  return (
    <nav className="bg-stone-dark border-b-4 border-black sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
        <Link href="/dungeon" className="font-display text-arcane text-sm tracking-wider">
          CODECRYPT
        </Link>

        <button
          className="md:hidden text-parchment"
          onClick={() => setOpen((v) => !v)}
          aria-label="Toggle menu"
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>

        <div className="hidden md:flex items-center gap-4">
          {LINKS.map((l) => (
            <NavLink key={l.href} {...l} active={pathname.startsWith(l.href)} />
          ))}
        </div>

        <div className="hidden md:flex items-center gap-3">
          <span className="font-body text-parchment-dim text-sm">{player?.username}</span>
          <button
            onClick={handleLogout}
            className="font-display text-[9px] bg-blood text-parchment px-2 py-2 border-2 border-black"
          >
            LOGOUT
          </button>
        </div>
      </div>

      {open && (
        <div className="md:hidden border-t-4 border-black bg-stone-dark px-4 py-3 flex flex-col gap-3">
          {LINKS.map((l) => (
            <NavLink key={l.href} {...l} active={pathname.startsWith(l.href)} onClick={() => setOpen(false)} />
          ))}
          <button
            onClick={handleLogout}
            className="font-display text-[9px] bg-blood text-parchment px-3 py-2 border-2 border-black self-start mt-1"
          >
            LOGOUT
          </button>
        </div>
      )}
    </nav>
  );
}

function NavLink({ href, label, icon: Icon, active, onClick }) {
  return (
    <Link
      href={href}
      onClick={onClick}
      className={clsx(
        'font-display text-[9px] flex items-center gap-2 px-2 py-2 border-2',
        active ? 'border-arcane text-arcane' : 'border-transparent text-parchment-dim hover:text-parchment'
      )}
    >
      <Icon size={14} />
      {label}
    </Link>
  );
}
