'use client';

import { useMemo } from 'react';

/**
 * Computes evenly-spaced chain-link positions along a straight segment.
 * Links alternate a 90-degree rotation so consecutive rings read as
 * interlocking, the way a real chain does.
 */
function chainLinkPoints(x1, y1, x2, y2, linkSpacing) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const dist = Math.sqrt(dx * dx + dy * dy);
  const count = Math.max(2, Math.round(dist / linkSpacing));
  const angle = (Math.atan2(dy, dx) * 180) / Math.PI;
  const points = [];
  for (let i = 0; i <= count; i++) {
    const t = i / count;
    points.push({
      x: x1 + dx * t,
      y: y1 + dy * t,
      rot: angle + (i % 2 === 0 ? 0 : 90),
    });
  }
  return points;
}

/**
 * A chain of oval links between two points -- the pixel-dungeon replacement
 * for a plain dashed <line>. Use inside any <svg> you already control the
 * coordinate space for (e.g. the dungeon map's own SVG, or a ReactFlow
 * viewport-driven overlay -- see MLDashboard.jsx's GraphChainOverlay, which
 * exists because ReactFlow 11's own custom-edge rendering path doesn't work
 * under this project's React 19).
 */
export default function ChainLink({ x1, y1, x2, y2, linkSize = 11, thickness, color = '#4a4238' }) {
  const points = useMemo(
    () => chainLinkPoints(x1, y1, x2, y2, linkSize),
    [x1, y1, x2, y2, linkSize]
  );
  // Thin, wiry rings by default -- stroke scales with link size instead of a
  // fixed absolute, so it stays proportionally thin whether this is used at
  // dungeon-map scale or the much smaller AI-dashboard overlay scale.
  const strokeWidth = thickness ?? Math.max(0.75, linkSize * 0.1);
  const rx = linkSize * 0.36;
  const ry = linkSize * 0.56;

  return (
    <g className="pointer-events-none" opacity={0.65}>
      {points.map((p, i) => (
        <ellipse
          key={i}
          cx={p.x}
          cy={p.y}
          rx={rx}
          ry={ry}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          transform={`rotate(${p.rot} ${p.x} ${p.y})`}
        />
      ))}
    </g>
  );
}
