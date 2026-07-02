'use client';

import { useQuery } from '@tanstack/react-query';
import { useRequireAuth } from '@/lib/useRequireAuth';
import { useAuthStore } from '@/store/useAuthStore';
import { game } from '@/lib/api/client';
import { STAT_MAP, TOPIC_LABELS } from '@/lib/statMap';
import PixelPanel from '@/components/ui/PixelPanel';
import PixelBadge from '@/components/ui/PixelBadge';
import XPBar from '@/components/XPBar';

export default function StatSheetPage() {
  const { ready } = useRequireAuth();
  const { player } = useAuthStore();

  const { data, isLoading } = useQuery({
    queryKey: ['player', player?.player_id],
    queryFn: () => game.getPlayer(player.player_id),
    enabled: ready && !!player,
  });

  if (!ready || !player) return null;

  const accuracies = data?.topic_accuracies || {};

  return (
    <div className="max-w-3xl mx-auto flex flex-col gap-5">
      <PixelPanel variant="arcane">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <div>
            <h1 className="font-display text-sm text-parchment">{player.username}</h1>
            <div className="flex gap-2 mt-2">
              <PixelBadge tone="gold">🔥 {player.streak_days} day streak</PixelBadge>
              <PixelBadge tone="arcane">{player.hint_tokens} hints left</PixelBadge>
            </div>
          </div>
          <div className="w-full md:w-60">
            <XPBar level={player.level} totalXp={player.total_xp} />
          </div>
        </div>
      </PixelPanel>

      <PixelPanel>
        <h2 className="font-display text-xs text-gold mb-4">CHARACTER STATS</h2>
        {isLoading ? (
          <p className="font-body text-parchment-dim">Reading your accuracy history…</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(STAT_MAP).map(([topic, { stat, flavor }]) => {
              const acc = accuracies[topic] ?? 0;
              return (
                <div key={topic} className="border-2 border-black p-3 bg-stone-dark">
                  <div className="flex justify-between items-baseline">
                    <span className="font-display text-[10px] text-parchment">{stat.toUpperCase()}</span>
                    <span className="font-body text-lg text-gold">{Math.round(acc * 100)}</span>
                  </div>
                  <p className="font-body text-sm text-parchment-dim mt-1">
                    {TOPIC_LABELS[topic]} — {flavor}
                  </p>
                  <div className="h-2 w-full bg-black border-2 border-black mt-2">
                    <div className="h-full bg-gold" style={{ width: `${Math.round(acc * 100)}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </PixelPanel>
    </div>
  );
}
