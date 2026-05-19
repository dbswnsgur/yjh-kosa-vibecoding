const BLOCK = 30;
const NEXT_BLOCK = 25;
const COLS = 10;
const ROWS = 20;

const COLORS = [
  null,
  '#00f5ff', // I - cyan
  '#ffd700', // O - yellow
  '#bf00ff', // T - purple
  '#39ff14', // S - green
  '#ff3131', // Z - red
  '#1f51ff', // J - blue
  '#ff8c00', // L - orange
];

const PIECES = [
  [[0,0,0,0],[1,1,1,1],[0,0,0,0],[0,0,0,0]], // I
  [[2,2],[2,2]],                               // O
  [[0,3,0],[3,3,3],[0,0,0]],                   // T
  [[0,4,4],[4,4,0],[0,0,0]],                   // S
  [[5,5,0],[0,5,5],[0,0,0]],                   // Z
  [[6,0,0],[6,6,6],[0,0,0]],                   // J
  [[0,0,7],[7,7,7],[0,0,0]],                   // L
];

const LINE_SCORES = [0, 100, 300, 500, 800];
const PREVENT_KEYS = new Set(['ArrowLeft', 'ArrowRight', 'ArrowDown', 'ArrowUp', ' ']);

// ===== BGM (Korobeiniki / Tetris Theme A) =====

const BPM = 144;
const BEAT = 60 / BPM;
const VOLUME = 0.1;

// [frequency Hz, beats]  —  0 = rest
const A4=440,B4=493.88,C5=523.25,D5=587.33,E5=659.25,F5=698.46,G5=783.99,A5=880;
const TETRIS_THEME = [
  // Part A - phrase 1
  [E5,1],[B4,.5],[C5,.5],[D5,1],[C5,.5],[B4,.5],
  [A4,1],[A4,.5],[C5,.5],[E5,1],[D5,.5],[C5,.5],
  // Part A - phrase 2
  [B4,1.5],[C5,.5],[D5,1],[E5,1],
  [C5,1],[A4,1],[A4,2],
  // Part B - phrase 1
  [0,.5],[D5,1.5],[F5,.5],[A5,1],[G5,.5],[F5,.5],
  [E5,1.5],[C5,.5],[E5,1],[D5,.5],[C5,.5],
  // Part B - phrase 2
  [B4,1],[B4,.5],[C5,.5],[D5,1],[E5,1],
  [C5,1],[A4,1],[A4,2],
];

let audioCtx = null;
let masterGain = null;
let isMuted = false;
let audioStarted = false;
let bgmLoopTimeout = null;

function initAudio() {
  if (audioStarted) return;
  audioStarted = true;
  audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  masterGain = audioCtx.createGain();
  masterGain.gain.value = VOLUME;
  masterGain.connect(audioCtx.destination);
  scheduleBGM(audioCtx.currentTime + 0.1);
}

function scheduleNote(freq, startTime, duration) {
  if (freq === 0) return;
  const osc = audioCtx.createOscillator();
  const noteGain = audioCtx.createGain();
  osc.type = 'square';
  osc.frequency.value = freq;
  // 간단한 어택/릴리즈 엔벨로프
  noteGain.gain.setValueAtTime(0.001, startTime);
  noteGain.gain.linearRampToValueAtTime(1.0, startTime + 0.01);
  noteGain.gain.setValueAtTime(1.0, startTime + duration * 0.82);
  noteGain.gain.linearRampToValueAtTime(0.001, startTime + duration * 0.97);
  osc.connect(noteGain);
  noteGain.connect(masterGain);
  osc.start(startTime);
  osc.stop(startTime + duration);
}

function scheduleBGM(startTime) {
  let t = startTime;
  TETRIS_THEME.forEach(([freq, beats]) => {
    scheduleNote(freq, t, beats * BEAT * 0.93);
    t += beats * BEAT;
  });
  const loopMs = (t - startTime) * 1000;
  bgmLoopTimeout = setTimeout(() => {
    if (audioCtx && audioStarted) scheduleBGM(audioCtx.currentTime + 0.05);
  }, loopMs - 150);
}

function toggleMute() {
  isMuted = !isMuted;
  if (masterGain) {
    masterGain.gain.setValueAtTime(isMuted ? 0 : VOLUME, audioCtx.currentTime);
  }
  document.getElementById('mute-btn').textContent = isMuted ? '🔇' : '🔊';
}

// ===== Game Logic =====

let canvas, ctx, nextCanvas, nextCtx;
let board, piece, nextPiece;
let score, level, lines;
let gameOver;
let dropTimer, lastTime, dropInterval;
let animFrameId = null;
let scoreSubmitted = false;
let globalBest = 0;

function init() {
  canvas = document.getElementById('board');
  ctx = canvas.getContext('2d');
  nextCanvas = document.getElementById('next-canvas');
  nextCtx = nextCanvas.getContext('2d');

  canvas.width = COLS * BLOCK;
  canvas.height = ROWS * BLOCK;
  nextCanvas.width = 4 * NEXT_BLOCK;
  nextCanvas.height = 4 * NEXT_BLOCK;

  document.addEventListener('keydown', handleKey);
  document.getElementById('restart-btn').addEventListener('click', () => {
    initAudio();
    startGame();
  });
  document.getElementById('mute-btn').addEventListener('click', () => {
    initAudio();
    toggleMute();
  });

  loadBestScore();
  startGame();
}

async function loadBestScore() {
  try {
    const res = await fetch('/api/scores/leaderboard?limit=1');
    if (!res.ok) return;
    const data = await res.json();
    if (data.length) {
      globalBest = data[0].score;
      updateBestUI(data[0].score, data[0].username);
    }
  } catch {}
}

function updateBestUI(score, username) {
  const scoreEl = document.getElementById('best-score');
  const userEl = document.getElementById('best-user');
  if (scoreEl) scoreEl.textContent = score.toLocaleString();
  if (userEl) userEl.textContent = username || '';
}

function startGame() {
  if (animFrameId !== null) {
    cancelAnimationFrame(animFrameId);
    animFrameId = null;
  }

  board = Array.from({ length: ROWS }, () => Array(COLS).fill(0));
  score = 0;
  level = 1;
  lines = 0;
  gameOver = false;
  dropTimer = 0;
  lastTime = 0;
  dropInterval = 1000;
  scoreSubmitted = false;
  setScoreMsg('');

  updateUI();
  nextPiece = randomPiece();
  spawnPiece();
  animFrameId = requestAnimationFrame(loop);
}

function randomPiece() {
  const matrix = PIECES[Math.floor(Math.random() * PIECES.length)];
  return { matrix: matrix.map(r => [...r]), x: 0, y: 0 };
}

function spawnPiece() {
  piece = nextPiece;
  piece.x = Math.floor((COLS - piece.matrix[0].length) / 2);
  piece.y = 0;
  nextPiece = randomPiece();

  if (collides(piece.matrix, piece.x, piece.y)) {
    gameOver = true;
  }

  drawNext();
}

function collides(matrix, px, py) {
  for (let r = 0; r < matrix.length; r++) {
    for (let c = 0; c < matrix[r].length; c++) {
      if (matrix[r][c] && (
        py + r >= ROWS ||
        px + c < 0 ||
        px + c >= COLS ||
        board[py + r][px + c]
      )) return true;
    }
  }
  return false;
}

function rotate(matrix) {
  const rows = matrix.length;
  const cols = matrix[0].length;
  const result = Array.from({ length: cols }, () => Array(rows).fill(0));
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      result[c][rows - 1 - r] = matrix[r][c];
    }
  }
  return result;
}

function lockPiece() {
  piece.matrix.forEach((row, r) => {
    row.forEach((val, c) => {
      if (val) board[piece.y + r][piece.x + c] = val;
    });
  });

  const cleared = clearLines();
  if (cleared > 0) {
    score += LINE_SCORES[cleared] * level;
    lines += cleared;
    level = Math.floor(lines / 10) + 1;
    dropInterval = Math.max(100, 1000 - (level - 1) * 100);
    updateUI();
  }

  spawnPiece();
}

function clearLines() {
  let count = 0;
  for (let r = ROWS - 1; r >= 0; r--) {
    if (board[r].every(cell => cell !== 0)) {
      board.splice(r, 1);
      board.unshift(Array(COLS).fill(0));
      count++;
      r++;
    }
  }
  return count;
}

function hardDrop() {
  while (!collides(piece.matrix, piece.x, piece.y + 1)) piece.y++;
  lockPiece();
}

function handleKey(e) {
  if (PREVENT_KEYS.has(e.key)) e.preventDefault();
  initAudio();

  if (gameOver) {
    if (e.key === 'Enter') startGame();
    return;
  }

  switch (e.key) {
    case 'ArrowLeft':
      if (!collides(piece.matrix, piece.x - 1, piece.y)) piece.x--;
      break;
    case 'ArrowRight':
      if (!collides(piece.matrix, piece.x + 1, piece.y)) piece.x++;
      break;
    case 'ArrowDown':
      if (!collides(piece.matrix, piece.x, piece.y + 1)) piece.y++;
      else lockPiece();
      break;
    case 'ArrowUp':
    case 'z':
    case 'Z': {
      const rotated = rotate(piece.matrix);
      if (!collides(rotated, piece.x, piece.y)) {
        piece.matrix = rotated;
      } else if (!collides(rotated, piece.x + 1, piece.y)) {
        piece.matrix = rotated; piece.x++;
      } else if (!collides(rotated, piece.x - 1, piece.y)) {
        piece.matrix = rotated; piece.x--;
      }
      break;
    }
    case ' ':
      hardDrop();
      break;
  }

  draw();
}

function loop(timestamp) {
  if (gameOver) {
    draw();
    drawGameOver();
    if (!scoreSubmitted) {
      scoreSubmitted = true;
      saveScore();
    }
    animFrameId = null;
    return;
  }

  if (lastTime === 0) lastTime = timestamp;
  const delta = timestamp - lastTime;
  lastTime = timestamp;
  dropTimer += delta;

  if (dropTimer >= dropInterval) {
    dropTimer = 0;
    if (!collides(piece.matrix, piece.x, piece.y + 1)) {
      piece.y++;
    } else {
      lockPiece();
    }
  }

  draw();
  animFrameId = requestAnimationFrame(loop);
}

function draw() {
  ctx.fillStyle = '#16213e';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.strokeStyle = '#1e3060';
  ctx.lineWidth = 0.5;
  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) {
      ctx.strokeRect(c * BLOCK, r * BLOCK, BLOCK, BLOCK);
    }
  }

  board.forEach((row, r) => {
    row.forEach((val, c) => {
      if (val) drawBlock(ctx, c, r, COLORS[val], BLOCK);
    });
  });

  if (gameOver) return;

  // 고스트 피스
  let ghostY = piece.y;
  while (!collides(piece.matrix, piece.x, ghostY + 1)) ghostY++;
  if (ghostY !== piece.y) {
    piece.matrix.forEach((row, r) => {
      row.forEach((val, c) => {
        if (val) {
          ctx.fillStyle = 'rgba(255,255,255,0.12)';
          ctx.fillRect((piece.x + c) * BLOCK + 1, (ghostY + r) * BLOCK + 1, BLOCK - 2, BLOCK - 2);
        }
      });
    });
  }

  piece.matrix.forEach((row, r) => {
    row.forEach((val, c) => {
      if (val) drawBlock(ctx, piece.x + c, piece.y + r, COLORS[val], BLOCK);
    });
  });
}

function drawBlock(context, x, y, color, size) {
  context.fillStyle = color;
  context.fillRect(x * size + 1, y * size + 1, size - 2, size - 2);
  context.fillStyle = 'rgba(255,255,255,0.28)';
  context.fillRect(x * size + 2, y * size + 2, size - 4, 3);
  context.fillRect(x * size + 2, y * size + 2, 3, size - 4);
  context.fillStyle = 'rgba(0,0,0,0.25)';
  context.fillRect(x * size + 1, y * size + size - 4, size - 2, 3);
}

function drawNext() {
  nextCtx.fillStyle = '#16213e';
  nextCtx.fillRect(0, 0, nextCanvas.width, nextCanvas.height);

  const offsetX = Math.floor((4 - nextPiece.matrix[0].length) / 2);
  const offsetY = Math.floor((4 - nextPiece.matrix.length) / 2);

  nextPiece.matrix.forEach((row, r) => {
    row.forEach((val, c) => {
      if (val) drawBlock(nextCtx, offsetX + c, offsetY + r, COLORS[val], NEXT_BLOCK);
    });
  });
}

function drawGameOver() {
  ctx.fillStyle = 'rgba(0,0,0,0.72)';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.textAlign = 'center';
  ctx.fillStyle = '#ff3131';
  ctx.font = 'bold 30px "Courier New", monospace';
  ctx.fillText('GAME OVER', canvas.width / 2, canvas.height / 2 - 18);

  ctx.fillStyle = '#aabbcc';
  ctx.font = '14px "Courier New", monospace';
  ctx.fillText('Enter 또는 RESTART 버튼', canvas.width / 2, canvas.height / 2 + 16);
}

function updateUI() {
  document.getElementById('score').textContent = score;
  document.getElementById('level').textContent = level;
  document.getElementById('lines').textContent = lines;
}

function setScoreMsg(msg, color = '#6677aa') {
  const el = document.getElementById('score-msg');
  if (!el) return;
  el.textContent = msg;
  el.style.color = color;
}

async function saveScore() {
  if (!window.backendAvailable) {
    setScoreMsg('서버 미연결 — 점수 저장 불가');
    return;
  }
  if (typeof Auth === 'undefined' || !Auth.isLoggedIn()) {
    setScoreMsg('로그인하면 점수가 저장됩니다');
    return;
  }
  setScoreMsg('저장 중...');
  try {
    const saveRes = await Auth.fetchWithAuth('/api/scores', {
      method: 'POST',
      body: JSON.stringify({ score, level, lines }),
    });
    if (!saveRes || !saveRes.ok) {
      setScoreMsg('저장 실패', '#ff3131');
      return;
    }

    // 순위 조회
    const rankRes = await fetch(`/api/scores/rank?score=${score}`);
    if (rankRes.ok) {
      const { rank, total } = await rankRes.json();
      const isNewBest = score > globalBest;
      if (isNewBest) {
        globalBest = score;
        updateBestUI(score, Auth.getUsername());
        setScoreMsg(`신기록! 전체 ${rank}위 / ${total}명`, '#ffd700');
      } else {
        setScoreMsg(`전체 ${rank}위 / ${total}명`, '#39ff14');
      }
    } else {
      setScoreMsg('점수 저장됨!', '#39ff14');
    }
  } catch {
    setScoreMsg('저장 실패', '#ff3131');
  }
}

window.addEventListener('load', init);
