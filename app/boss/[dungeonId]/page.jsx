'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useRequireAuth } from '@/lib/useRequireAuth';
import { useGameStore } from '@/store/useGameStore';
import { useAuthStore } from '@/store/useAuthStore';
import PixelPanel from '@/components/ui/PixelPanel';
import PixelButton from '@/components/ui/PixelButton';
import PixelInput from '@/components/ui/PixelInput';
import PixelBadge from '@/components/ui/PixelBadge';
import HealthBar from '@/components/HealthBar';
import HintToken from '@/components/HintToken';
import DamageNumber from '@/components/DamageNumber';

const VERDICT_TONE = { correct: 'arcane', partial: 'gold', incorrect: 'blood' };
const BOSS_TOPIC = 'boss';

export default function BossFightPage() {
  const { ready } = useRequireAuth();
  const router = useRouter();

  const { player, spendHintToken, fetchMe } = useAuthStore();
  const {
    currentQuestion,
    combat,
    enteringRoom,
    lastResult,
    submitting,
    submitError,
    hintRevealed,
    enterRoom,
    submitAnswer,
    useHintLocally,
    resetCombat,
    retreat,
  } = useGameStore();

  const [answer, setAnswer] = useState('');
  const [floats, setFloats] = useState([]);

  useEffect(() => {
    if (ready) enterRoom(BOSS_TOPIC);
    return () => resetCombat();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready]);

  useEffect(() => {
    if (!lastResult) return;
    fetchMe();
    const id = Date.now();
    const text =
      lastResult.verdict === 'correct'
        ? `-${Math.round(25 * lastResult.damage_multiplier)} HP  +${lastResult.xp_gained} XP`
        : lastResult.verdict === 'partial'
        ? `-${Math.round(25 * lastResult.damage_multiplier)} HP`
        : 'MISS';
    setFloats((f) => [...f, { id, text, tone: lastResult.verdict === 'incorrect' ? 'damage' : 'xp' }]);
    const t = setTimeout(() => setFloats((f) => f.filter((x) => x.id !== id)), 1000);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lastResult]);

  if (!ready) return null;

  if (submitError && !currentQuestion) {
    return (
      <div className="max-w-xl mx-auto text-center mt-10">
        <p className="font-body text-blood text-lg">{submitError}</p>
        <PixelButton className="mt-4" onClick={() => router.push('/dungeon')}>
          BACK TO THE DUNGEON
        </PixelButton>
      </div>
    );
  }

  if (enteringRoom && !currentQuestion) {
    return (
      <p className="font-body text-ember text-center mt-10 animate-flicker">
        The dungeon shakes. The Big-O Devourer awakens…
      </p>
    );
  }

  if (!currentQuestion || !combat) return null;

  const bossDefeated = combat.enemyHp <= 0;
  const playerDefeated = combat.playerHp <= 0;
  const fightOver = bossDefeated || playerDefeated;

  async function handleSubmit(e) {
    e.preventDefault();
    if (!answer.trim() || submitting) return;
    await submitAnswer(answer);
    setAnswer('');
  }

  async function handleContinue() {
    setAnswer('');
    await enterRoom(BOSS_TOPIC);
  }

  function handleVictory() {
    resetCombat();
    router.push('/dungeon');
  }

  async function handleRetreat() {
    await retreat();
    router.push('/dungeon');
  }

  return (
    <div className="max-w-2xl mx-auto flex flex-col gap-5">
      <div className="text-center">
        <h1 className="font-display text-sm text-ember">BOSS ENCOUNTER</h1>
        <p className="font-body text-parchment-dim">Every question pulls from a different topic. Stay sharp.</p>
      </div>

      <PixelPanel className="border-ember">
        <div className="flex justify-between items-center mb-2">
          <span className="font-display text-[10px] text-ember">THE BIG-O DEVOURER</span>
          <PixelBadge tone="ember">{currentQuestion.difficulty}</PixelBadge>
        </div>
        <DamageNumber items={floats} />
        <HealthBar current={combat.enemyHp} max={combat.enemyHpMax} label="BOSS" kind="enemy" />
      </PixelPanel>

      <PixelPanel>
        <HealthBar current={combat.playerHp} max={combat.playerHpMax} label={player.username.toUpperCase()} kind="player" />
      </PixelPanel>

      <PixelPanel>
        <p className="font-body text-xl text-parchment leading-relaxed">{currentQuestion.question}</p>
        {hintRevealed && <p className="font-body text-arcane mt-3 text-base">💡 {currentQuestion.hint}</p>}
        <div className="mt-3">
          <HintToken
            tokensRemaining={player.hint_tokens}
            maxTokens={3}
            used={hintRevealed}
            onUse={() => useHintLocally(spendHintToken)}
          />
        </div>
      </PixelPanel>

      {!fightOver && !lastResult && (
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <PixelInput
            id="boss-answer"
            label="YOUR ANSWER"
            textarea
            rows={4}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            disabled={submitting}
          />
          <PixelButton type="submit" variant="primary" disabled={submitting || !answer.trim()}>
            {submitting ? 'THE JUDGE CONSIDERS…' : 'STRIKE'}
          </PixelButton>
        </form>
      )}

      {lastResult && !fightOver && (
        <PixelPanel>
          <PixelBadge tone={VERDICT_TONE[lastResult.verdict]}>{lastResult.verdict.toUpperCase()}</PixelBadge>
          <p className="font-body text-lg mt-2">{lastResult.feedback}</p>
          <PixelButton variant="ghost" className="mt-4" onClick={handleContinue}>
            CONTINUE
          </PixelButton>
        </PixelPanel>
      )}

      {bossDefeated && (
        <PixelPanel variant="arcane">
          <h2 className="font-display text-sm text-gold mb-2">THE DUNGEON FALLS SILENT</h2>
          <p className="font-body text-lg">You&apos;ve cleared the dungeon. The Devourer dissolves into data.</p>
          <PixelButton variant="gold" className="mt-4" onClick={handleVictory}>
            CLAIM VICTORY
          </PixelButton>
        </PixelPanel>
      )}

      {playerDefeated && (
        <PixelPanel>
          <h2 className="font-display text-sm text-blood mb-2">THE DEVOURER PREVAILS — FOR NOW</h2>
          <p className="font-body text-lg">Retreat, sharpen your weak topics, and return stronger.</p>
          <PixelButton variant="danger" className="mt-4" onClick={handleRetreat}>
            RETREAT
          </PixelButton>
        </PixelPanel>
      )}
    </div>
  );
}
