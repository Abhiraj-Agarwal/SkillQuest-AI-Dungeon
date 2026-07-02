'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useRequireAuth } from '@/lib/useRequireAuth';
import { useGameStore } from '@/store/useGameStore';
import { useAuthStore } from '@/store/useAuthStore';
import { TOPIC_LABELS } from '@/lib/statMap';
import PixelPanel from '@/components/ui/PixelPanel';
import PixelButton from '@/components/ui/PixelButton';
import PixelInput from '@/components/ui/PixelInput';
import PixelBadge from '@/components/ui/PixelBadge';
import HealthBar from '@/components/HealthBar';
import HintToken from '@/components/HintToken';
import DamageNumber from '@/components/DamageNumber';

const VERDICT_TONE = { correct: 'arcane', partial: 'gold', incorrect: 'blood' };

export default function CombatPage() {
  const { ready } = useRequireAuth();
  const params = useParams();
  const router = useRouter();
  const topic = params.roomId;

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
    revealHintLocally,
    resetCombat,
    retreat,
  } = useGameStore();

  const [answer, setAnswer] = useState('');
  const [floats, setFloats] = useState([]);

  useEffect(() => {
    if (ready && topic) enterRoom(topic);
    return () => resetCombat();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, topic]);

  useEffect(() => {
    if (!lastResult) return;
    fetchMe(); // resync level/xp/hint_tokens after the backend updates them
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

  if (enteringRoom && !currentQuestion) {
    return (
      <p className="font-body text-arcane text-center mt-10 animate-flicker">
        The {TOPIC_LABELS[topic] || topic} wraith stirs… generating a challenge.
      </p>
    );
  }

  if (!currentQuestion || !combat) {
    return <p className="font-body text-blood text-center mt-10">{submitError || 'No active fight.'}</p>;
  }

  const enemyDefeated = combat.enemyHp <= 0;
  const playerDefeated = combat.playerHp <= 0;
  const fightOver = enemyDefeated || playerDefeated;

  async function handleSubmit(e) {
    e.preventDefault();
    if (!answer.trim() || submitting) return;
    await submitAnswer(answer);
    setAnswer('');
  }

  async function handleContinue() {
    setAnswer('');
    await enterRoom(topic);
  }

  async function handleClaimVictory() {
    resetCombat();
    router.push('/dungeon');
  }

  async function handleRetreat() {
    await retreat();
    router.push('/dungeon');
  }

  return (
    <div className="max-w-2xl mx-auto flex flex-col gap-5">
      <PixelPanel variant="arcane">
        <div className="flex justify-between items-center mb-2">
          <span className="font-display text-[10px] text-ember">{combat.enemyName}</span>
          <PixelBadge tone={combat.enemyName.includes('Devourer') ? 'ember' : 'arcane'}>
            {currentQuestion.difficulty}
          </PixelBadge>
        </div>
        <DamageNumber items={floats} />
        <HealthBar current={combat.enemyHp} max={combat.enemyHpMax} label="ENEMY" kind="enemy" />
      </PixelPanel>

      <PixelPanel>
        <HealthBar current={combat.playerHp} max={combat.playerHpMax} label={player.username.toUpperCase()} kind="player" />
      </PixelPanel>

      <PixelPanel>
        <p className="font-body text-xl text-parchment leading-relaxed">{currentQuestion.question}</p>
        {hintRevealed && (
          <p className="font-body text-arcane mt-3 text-base">💡 {currentQuestion.hint}</p>
        )}
        <div className="mt-3">
          <HintToken
            tokensRemaining={player.hint_tokens}
            maxTokens={3}
            used={hintRevealed}
            onUse={() => revealHintLocally(spendHintToken)}
          />
        </div>
      </PixelPanel>

      {!fightOver && !lastResult && (
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <PixelInput
            id="answer"
            label="YOUR ANSWER"
            textarea
            rows={4}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Explain your answer — paraphrasing is fine, the judge reads for meaning."
            disabled={submitting}
          />
          <PixelButton type="submit" disabled={submitting || !answer.trim()}>
            {submitting ? 'THE JUDGE CONSIDERS…' : 'ATTACK'}
          </PixelButton>
        </form>
      )}

      {lastResult && !fightOver && (
        <PixelPanel>
          <PixelBadge tone={VERDICT_TONE[lastResult.verdict]}>{lastResult.verdict.toUpperCase()}</PixelBadge>
          <p className="font-body text-lg mt-2">{lastResult.feedback}</p>
          <PixelButton variant="ghost" className="mt-4" onClick={handleContinue}>
            CONTINUE FIGHT
          </PixelButton>
        </PixelPanel>
      )}

      {enemyDefeated && (
        <PixelPanel variant="arcane">
          <h2 className="font-display text-sm text-gold mb-2">VICTORY</h2>
          <p className="font-body text-lg">{lastResult?.feedback}</p>
          <PixelButton variant="gold" className="mt-4" onClick={handleClaimVictory}>
            RETURN TO THE DUNGEON
          </PixelButton>
        </PixelPanel>
      )}

      {playerDefeated && (
        <PixelPanel>
          <h2 className="font-display text-sm text-blood mb-2">YOU HAVE FALLEN</h2>
          <p className="font-body text-lg">The wraith overwhelms you. Retreat and heal before trying again.</p>
          <PixelButton variant="danger" className="mt-4" onClick={handleRetreat}>
            RETREAT
          </PixelButton>
        </PixelPanel>
      )}
    </div>
  );
}
