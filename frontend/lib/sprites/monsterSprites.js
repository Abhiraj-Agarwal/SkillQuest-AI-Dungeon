// Hand-authored pixel-art monster sprites. Each entry is a { name, grid,
// palette } sprite definition consumed by <PixelSprite>. `grid` is an array
// of equal-length row strings; each character indexes into `palette` (hex
// color) or is '.' for transparent.
//
// TO ADD OR SWAP A MONSTER: add a new key to MONSTERS below (or edit an
// existing grid/palette in place), then point any topic at it in
// TOPIC_MONSTER. No other file needs to change -- everything that renders a
// villain (dungeon map tiles, combat/boss screens, the AI dashboard graph)
// reads through TOPIC_MONSTER / BOSS_MONSTER.

export const MONSTERS = {
  wraith: {
    name: 'Wraith',
    image: '/sprites/monsters/wraith.png',
    palette: { k: '#0c0a14', b: '#3a8c7c', g: '#6ee7d0', e: '#ece3cf' },
    grid: [
      '................',
      '......kkkk......',
      '....kkbbbbkk....',
      '...kbbggbbggbk..',
      '..kbbbeebeebbbk.',
      '..kbbbeebeebbbk.',
      '.kbbbbbbbbbbbbk.',
      '.kbbbbggggbbbbk.',
      '.kbbbbbbbbbbbbk.',
      '.kbbbbbbbbbbbbk.',
      '.kbbbbbbbbbbbbk.',
      '.kbbbbbbbbbbbbk.',
      '.kbb.bb.bb.bbbk.',
      '.kb.bb.bb.bb.bk.',
      '.k.b......b...k.',
      '................',
    ],
  },

  skeleton: {
    name: 'Bone Sentinel',
    image: '/sprites/monsters/skeleton.png',
    palette: { k: '#0c0a14', w: '#ece3cf', d: '#a89f8c', e: '#c43d3d' },
    grid: [
      '................',
      '......kkkk......',
      '.....kwwwwk.....',
      '.....kwewewk....',
      '.....kwwwwk.....',
      '......kdk.......',
      '.....kkkkkk.....',
      '....kwkkkkwk....',
      '....kw.kk.wk....',
      '.....kwwwwk.....',
      '......kwk.......',
      '.....kk.kk......',
      '.....kk.kk......',
      '.....kk.kk......',
      '....kkk.kkk.....',
      '................',
    ],
  },

  imp: {
    name: 'Ember Imp',
    image: '/sprites/monsters/imp.png',
    palette: { k: '#0c0a14', r: '#ff6b3d', d: '#b8492a', e: '#e8b339' },
    grid: [
      '................',
      '....k......k....',
      '....kk....kk....',
      '.....kkkkkk.....',
      '....krrrrrrk....',
      '...krreerrerk...',
      '...krrrrrrrrk...',
      '...krddddddrk...',
      '....krrrrrrk....',
      '.....krrrrk.....',
      '....kk.kk.kk....',
      '...kk..kk..kk...',
      '................',
      '................',
      '................',
      '................',
    ],
  },

  golem: {
    name: 'Stone Golem',
    image: '/sprites/monsters/golem.png',
    palette: { k: '#0c0a14', s: '#3d3450', l: '#2a2438', e: '#6ee7d0' },
    grid: [
      '................',
      '.....kkkkkk.....',
      '.....ksssssk....',
      '.....kseesk.....',
      '....ksssssssk...',
      '....ks.ss.sk....',
      '....ksssssssk...',
      '...kssssssssk...',
      '...kssssssssk...',
      '....ks.ss.sk....',
      '.....kssssk.....',
      '.....k.ss.k.....',
      '.....k.ss.k.....',
      '....kk.ss.kk....',
      '....kk....kk....',
      '................',
    ],
  },

  dragon: {
    name: 'The Big-O Devourer',
    image: '/sprites/monsters/dragon.png',
    palette: { k: '#0c0a14', d: '#ff6b3d', l: '#b8492a', e: '#e8b339' },
    grid: [
      '................',
      '.....k....k.....',
      '....kk....kk....',
      '...kddddddddk...',
      '..kdddddddddddk.',
      '.kddeeddddeeddk.',
      '.kddddddddddddk.',
      '.kdllllllllldk..',
      'kddddddddddddddk',
      'kdllllllllllllk.',
      '.kddddddddddddk.',
      '.kdd.dddddd.ddk.',
      '..kd.d....d.dk..',
      '...kk......kk...',
      '................',
      '................',
    ],
  },
};

// One fixed villain per topic -- the fight is the whole room (every question
// in it), not a new monster per question. Grouped roughly by knowledge-graph
// depth so later, harder topics read as tougher-looking enemies.
export const TOPIC_MONSTER = {
  arrays: 'wraith',
  linked_lists: 'skeleton',
  stacks_queues: 'skeleton',
  binary_search: 'wraith',
  recursion: 'imp',
  trees: 'imp',
  binary_search_tree: 'golem',
  heaps: 'golem',
  graphs: 'golem',
  dynamic_programming: 'imp',
  sorting_algorithms: 'skeleton',
};

export const BOSS_MONSTER = 'dragon';

export function monsterForTopic(topic) {
  const id = topic === 'boss' ? BOSS_MONSTER : TOPIC_MONSTER[topic];
  return MONSTERS[id] || MONSTERS.wraith;
}
