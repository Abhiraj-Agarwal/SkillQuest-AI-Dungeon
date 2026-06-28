'use client';

import { useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { Lock, Sword, Crown } from 'lucide-react';
import clsx from 'clsx';
import { useRequireAuth } from '@/lib/useRequireAuth';
import { useGameStore } from '@/store/useGameStore';
import { useAuthStore } from '@/store/useAuthStore';
import { layoutGraph } from '@/lib/graphLayout';
import { DUNGEON_ID } from '@/lib/config';
import PixelPanel from '@/components/ui/PixelPanel';
import PixelBadge from '@/components/ui/PixelBadge';
import XPBar from '@/components/XPBar';

const STATUS_STYLE = {
  locked: 'bg-stone-light border-black opacity-50',
  unlocked: 'bg-stone border-arcane',
  weak: 'bg-stone border-blood',
  mastered: 'bg-stone border-gold',
};

export default function DungeonMapPage() {
  const { ready } = useRequireAuth();
  const router = useRouter();
  const { player } = useAuthStore();
  const { dungeon, loadingDungeon, dungeonError, loadDungeon } = useGameStore();

  useEffect(() => {
    if (ready) loadDungeon(DUNGEON_ID);
  }, [ready, loadDungeon]);

  const positions = useMemo(() => layoutGraph({ colWidth: 170, rowHeight: 120 }), []);

  if (!ready || loadingDungeon || !dungeon) {
    return <p className="font-body text-parchment-dim text-center mt-10">Descending into the dungeon…</p>;
  }
  if (dungeonError) {
    return <p className="font-body text-blood text-center mt-10">{dungeonError}</p>;
  }

  const xs = dungeon.rooms.map((r) => positions[r.topic]?.x ?? 0);
  const ys = dungeon.rooms.map((r) => positions[r.topic]?.y ?? 0);
  const minX = Math.min(...xs);
  const maxY = Math.max(...ys);
  const offsetX = -minX + 80;
  const tile = 150;

  const edges = [];
  dungeon.rooms.forEach((r) => {
    r.prerequisites.forEach((pre) => {
      edges.push({ from: pre, to: r.topic });
    });
  });

  return (
    <div>
      <div className="mb-6 flex flex-col md:flex-row gap-4 md:items-center md:justify-between">
        <div>
          <h1 className="font-display text-sm text-parchment">{dungeon.domain}</h1>
          {dungeon.next_topic && (
            <p className="font-body text-arcane mt-1">
              The dungeon senses weakness in <strong>{labelFor(dungeon, dungeon.next_topic)}</strong>.
            </p>
          )}
        </div>
        <div className="w-full md:w-64">
          <XPBar level={player.level} totalXp={player.total_xp} />
        </div>
      </div>

      <PixelPanel className="overflow-x-auto">
        <div
          className="relative mx-auto"
          style={{ width: offsetX * 2 + tile, height: maxY + tile + 100, minWidth: 600 }}
        >
          <svg className="absolute inset-0 w-full h-full pointer-events-none">
            {edges.map((e, i) => {
              const from = positions[e.from];
              const to = positions[e.to];
              if (!from || !to) return null;
              return (
                <line
                  key={i}
                  x1={from.x + offsetX + tile / 2}
                  y1={from.y + tile / 2}
                  x2={to.x + offsetX + tile / 2}
                  y2={to.y + tile / 2}
                  stroke="#6ee7d0"
                  strokeOpacity={0.35}
                  strokeWidth={3}
                  strokeDasharray="6 4"
                />
              );
            })}
          </svg>

          {dungeon.rooms.map((room) => {
            const pos = positions[room.topic];
            if (!pos) return null;
            const locked = room.status === 'locked';
            return (
              <button
                key={room.topic}
                disabled={locked}
                onClick={() => router.push(`/combat/${room.topic}`)}
                style={{ left: pos.x + offsetX, top: pos.y, width: tile, height: tile - 20 }}
                className={clsx(
                  'absolute flex flex-col items-center justify-center gap-2 border-4 p-2 transition-transform',
                  'hover:-translate-y-1 disabled:hover:translate-y-0 disabled:cursor-not-allowed',
                  STATUS_STYLE[room.status]
                )}
              >
                {locked ? <Lock size={18} /> : <Sword size={18} />}
                <span className="font-display text-[8px] text-parchment text-center leading-tight">
                  {room.label}
                </span>
                {!locked && (
                  <span className="font-body text-sm text-parchment-dim">
                    {Math.round(room.recent_accuracy * 100)}%
                  </span>
                )}
              </button>
            );
          })}

          {/* boss room, one row below the deepest topic */}
          <button
            disabled={!dungeon.boss_unlocked}
            onClick={() => router.push(`/boss/${DUNGEON_ID}`)}
            style={{ left: offsetX + tile / 4, top: maxY + tile, width: tile * 1.5, height: tile - 10 }}
            className={clsx(
              'absolute flex flex-col items-center justify-center gap-2 border-4 p-2',
              dungeon.boss_unlocked ? 'bg-stone border-ember' : 'bg-stone-light border-black opacity-50'
            )}
          >
            {dungeon.boss_unlocked ? <Crown size={20} className="text-ember" /> : <Lock size={18} />}
            <span className="font-display text-[8px] text-parchment text-center">
              {dungeon.boss_unlocked ? 'THE BIG-O DEVOURER' : 'CLEAR ALL ROOMS FIRST'}
            </span>
          </button>
        </div>
      </PixelPanel>

      <div className="flex gap-3 mt-4 flex-wrap">
        <PixelBadge tone="arcane">unlocked</PixelBadge>
        <PixelBadge tone="blood">weak — needs practice</PixelBadge>
        <PixelBadge tone="gold">mastered</PixelBadge>
        <PixelBadge tone="stone">locked</PixelBadge>
      </div>
    </div>
  );
}

function labelFor(dungeon, topic) {
  return dungeon.rooms.find((r) => r.topic === topic)?.label || topic;
}
