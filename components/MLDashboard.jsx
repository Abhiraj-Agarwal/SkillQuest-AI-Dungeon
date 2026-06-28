'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import ReactFlow, { Background, Handle, Position } from 'reactflow';
import 'reactflow/dist/style.css';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { ai } from '@/lib/api/client';
import { layoutGraph } from '@/lib/graphLayout';
import PixelPanel from './ui/PixelPanel';
import PixelBadge from './ui/PixelBadge';

const STATUS_COLOR = {
  locked: '#3d3450',
  unlocked: '#6ee7d0',
  weak: '#c43d3d',
  mastered: '#e8b339',
};

const DIFFICULTY_VALUE = { easy: 1, medium: 2, hard: 3 };

function StoneNode({ data }) {
  return (
    <div
      className="font-display text-[8px] text-center px-2 py-2 border-4 border-black bg-stone"
      style={{ width: 140, boxShadow: `0 0 0 2px ${STATUS_COLOR[data.status]}` }}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#000' }} />
      <div className="text-parchment leading-tight">{data.label}</div>
      <div className="font-body text-sm mt-1" style={{ color: STATUS_COLOR[data.status] }}>
        {Math.round(data.accuracy * 100)}%
      </div>
      <Handle type="source" position={Position.Bottom} style={{ background: '#000' }} />
    </div>
  );
}

const nodeTypes = { stone: StoneNode };

export default function MLDashboard({ playerId }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard', playerId],
    queryFn: () => ai.getDashboard(playerId),
    enabled: !!playerId,
    refetchInterval: 6000, // polling default per integration contract
  });

  const { nodes, edges } = useMemo(() => {
    if (!data?.graph) return { nodes: [], edges: [] };
    const positions = layoutGraph();
    const nodes = data.graph.nodes.map((n) => ({
      id: n.id,
      type: 'stone',
      position: positions[n.id] || { x: 0, y: 0 },
      data: n,
    }));
    const edges = data.graph.edges.map((e) => ({
      id: `${e.source}-${e.target}`,
      source: e.source,
      target: e.target,
      style: { stroke: '#6ee7d0', strokeWidth: 2 },
      animated: true,
    }));
    return { nodes, edges };
  }, [data]);

  const scoreChartData = useMemo(
    () => (data?.score_history || []).slice().reverse().map((s, i) => ({ idx: i + 1, score: s.score })),
    [data]
  );

  const difficultyChartData = useMemo(
    () =>
      (data?.difficulty_history || [])
        .slice()
        .reverse()
        .map((d, i) => ({ idx: i + 1, value: DIFFICULTY_VALUE[d.difficulty] || 1, topic: d.topic })),
    [data]
  );

  if (error) {
    return (
      <PixelPanel variant="arcane">
        <p className="font-body text-blood">Could not load the AI dashboard: {error.message}</p>
      </PixelPanel>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <PixelPanel variant="arcane" className="lg:col-span-2 h-[420px] relative">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-display text-xs text-arcane">KNOWLEDGE GRAPH</h3>
          <PixelBadge tone="arcane" className="animate-pulse">LIVE</PixelBadge>
        </div>
        {isLoading ? (
          <p className="font-body text-parchment-dim">Reading the dungeon&apos;s mind…</p>
        ) : (
          <div className="h-[340px]">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              fitView
              proOptions={{ hideAttribution: true }}
              nodesDraggable={false}
              nodesConnectable={false}
              elementsSelectable={false}
            >
              <Background color="#1a1523" gap={16} />
            </ReactFlow>
          </div>
        )}
        <Legend />
      </PixelPanel>

      <div className="flex flex-col gap-4">
        <PixelPanel>
          <h3 className="font-display text-xs text-gold mb-2">RL DIFFICULTY TUNER</h3>
          <ResponsiveContainer width="100%" height={130}>
            <LineChart data={difficultyChartData}>
              <CartesianGrid stroke="#1a1523" />
              <XAxis dataKey="idx" stroke="#a89f8c" fontSize={10} />
              <YAxis
                domain={[0, 3]}
                ticks={[1, 2, 3]}
                tickFormatter={(v) => ['', 'easy', 'med', 'hard'][v]}
                stroke="#a89f8c"
                fontSize={10}
              />
              <Tooltip
                contentStyle={{ background: '#1a1523', border: '2px solid #000', fontFamily: 'var(--font-vt323)' }}
                formatter={(v) => ['', 'easy', 'medium', 'hard'][v]}
              />
              <Line type="stepAfter" dataKey="value" stroke="#e8b339" strokeWidth={3} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </PixelPanel>

        <PixelPanel>
          <h3 className="font-display text-xs text-ember mb-2">NLP JUDGE SCORES</h3>
          <ResponsiveContainer width="100%" height={130}>
            <BarChart data={scoreChartData}>
              <CartesianGrid stroke="#1a1523" />
              <XAxis dataKey="idx" stroke="#a89f8c" fontSize={10} />
              <YAxis domain={[0, 1]} stroke="#a89f8c" fontSize={10} />
              <Tooltip contentStyle={{ background: '#1a1523', border: '2px solid #000', fontFamily: 'var(--font-vt323)' }} />
              <Bar dataKey="score" fill="#ff6b3d" />
            </BarChart>
          </ResponsiveContainer>
        </PixelPanel>
      </div>
    </div>
  );
}

function Legend() {
  return (
    <div className="flex gap-3 mt-2 flex-wrap">
      {Object.entries(STATUS_COLOR).map(([status, color]) => (
        <div key={status} className="flex items-center gap-1 font-body text-xs text-parchment-dim">
          <span className="w-3 h-3 border-2 border-black inline-block" style={{ backgroundColor: color }} />
          {status}
        </div>
      ))}
    </div>
  );
}
