/* ABC & 123 Adventure — kid app engine */
'use strict';

/* ---------------- utilities ---------------- */
function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
let rng = Math.random;
const rand = (n) => Math.floor(rng() * n);
const pick = (arr) => arr[rand(arr.length)];
function shuffle(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) { const j = rand(i + 1); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}
const todayKey = () => new Date().toISOString().slice(0, 10);

/* ---------------- progress store ---------------- */
const STORE_KEY = 'abc123.v1';

function defaultStore() {
  return {
    items: {},          // id -> {seen, correct, wrong, mastery}
    days: {},           // 'YYYY-MM-DD' -> seconds
    sessionCount: 0,
    totalRounds: 0,
    stickers: [],
    firstDay: todayKey(),
    learnedLog: [],     // [{id, label, day}] when an item reaches mastery
  };
}
function loadStore() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (raw) return Object.assign(defaultStore(), JSON.parse(raw));
  } catch (e) { /* corrupted storage -> start fresh */ }
  return defaultStore();
}
const store = loadStore();
function save() { try { localStorage.setItem(STORE_KEY, JSON.stringify(store)); } catch (e) {} }

function item(id) {
  if (!store.items[id]) store.items[id] = { seen: 0, correct: 0, wrong: 0, mastery: 0 };
  return store.items[id];
}
const MASTERED = 4;
function labelFor(id) {
  if (id.startsWith('L:')) return 'Letter ' + id.slice(2);
  if (id.startsWith('N:')) return 'Number ' + id.slice(2);
  if (id.startsWith('W:')) return 'Word ' + id.slice(2);
  return id;
}
function bumpCorrect(id) {
  const it = item(id);
  it.correct++;
  const before = it.mastery;
  it.mastery = Math.min(5, it.mastery + 1);
  if (before < MASTERED && it.mastery >= MASTERED) {
    store.learnedLog.push({ id, label: labelFor(id), day: todayKey() });
  }
  save();
}
function bumpWrong(id) { const it = item(id); it.wrong++; it.mastery = Math.max(0, it.mastery - 1); save(); }
function bumpSeen(id) { const it = item(id); it.seen++; if (it.mastery === 0) it.mastery = 1; save(); }

/* ---------------- time tracking ---------------- */
setInterval(() => {
  if (document.visibilityState === 'visible') {
    const k = todayKey();
    store.days[k] = (store.days[k] || 0) + 5;
    save();
  }
}, 5000);

/* ---------------- audio ---------------- */
let audioCtx = null;
function ctx() {
  if (!audioCtx) { try { audioCtx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) {} }
  if (audioCtx && audioCtx.state === 'suspended') audioCtx.resume();
  return audioCtx;
}
function tone(freq, dur, type, when, vol) {
  const c = ctx(); if (!c) return;
  const o = c.createOscillator(), g = c.createGain();
  o.type = type || 'sine'; o.frequency.value = freq;
  g.gain.setValueAtTime(vol || 0.18, c.currentTime + when);
  g.gain.exponentialRampToValueAtTime(0.001, c.currentTime + when + dur);
  o.connect(g); g.connect(c.destination);
  o.start(c.currentTime + when); o.stop(c.currentTime + when + dur + 0.05);
}
function sfx(kind) {
  if (kind === 'pop') tone(600 + rand(300), 0.12, 'triangle', 0, 0.25);
  else if (kind === 'yay') [523, 659, 784, 1047].forEach((f, i) => tone(f, 0.18, 'sine', i * 0.09));
  else if (kind === 'oops') tone(220, 0.25, 'sine', 0, 0.12);
  else if (kind === 'tap') tone(880, 0.08, 'square', 0, 0.08);
  else if (kind === 'sticker') [784, 988, 1175, 1568, 1976].forEach((f, i) => tone(f, 0.15, 'triangle', i * 0.07));
}
function speak(text, opts) {
  try {
    const u = new SpeechSynthesisUtterance(text);
    u.rate = (opts && opts.rate) || 0.85;
    u.pitch = (opts && opts.pitch) || 1.15;
    const voices = speechSynthesis.getVoices();
    const en = voices.find(v => /en[-_](US|GB|IN)/i.test(v.lang)) || voices.find(v => /^en/i.test(v.lang));
    if (en) u.voice = en;
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
  } catch (e) {}
}

/* ---------------- session setup (fresh every time) ---------------- */
store.sessionCount++;
save();
rng = mulberry32(store.sessionCount * 7919 + new Date().getDate() * 104729 + Date.now() % 100000);
const THEME = pick(THEMES);

/* ---------------- curriculum / adaptivity ---------------- */
function masteredCount(ids) { return ids.filter(id => item(id).mastery >= MASTERED).length; }

function letterTier() {
  const ids = LETTER_ORDER.map(l => 'L:' + l);
  const early = ids.slice(0, 8), mid = ids.slice(0, 16);
  if (masteredCount(early) < 6) return 1;             // meet uppercase letters
  if (masteredCount(mid) < 12) return 2;              // more letters + lowercase
  if (masteredCount(ids) < 20) return 3;              // phonics sounds
  return 4;                                           // first words
}
function numberTier() {
  const t1 = ['1','2','3','4','5'].map(n => 'N:' + n);
  const t2 = ['6','7','8','9','10'].map(n => 'N:' + n);
  if (masteredCount(t1) < 4) return 1;
  if (masteredCount(t2) < 4) return 2;
  if (masteredCount(Array.from({length: 20}, (_, i) => 'N:' + (i + 1))) < 16) return 3;
  return 4;                                           // sequences, more/less
}
function letterPool() {
  const t = letterTier();
  const n = t === 1 ? 8 : t === 2 ? 16 : 26;
  return LETTER_ORDER.slice(0, n);
}
function numberPool() {
  const t = numberTier();
  const max = t === 1 ? 5 : t === 2 ? 10 : 20;
  return Array.from({ length: max }, (_, i) => String(i + 1));
}
// Prefer items that are least known; occasionally review mastered ones.
function chooseTarget(pool, prefix) {
  const fresh = pool.filter(v => item(prefix + v).mastery < MASTERED);
  if (fresh.length && rng() > 0.15) {
    const sorted = shuffle(fresh).sort((a, b) => item(prefix + a).mastery - item(prefix + b).mastery);
    return sorted[rand(Math.min(3, sorted.length))];
  }
  return pick(pool);
}

/* ---------------- UI helpers ---------------- */
const stage = () => document.getElementById('stage');
const el = (tag, cls, text) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
};
function clearStage() { stage().innerHTML = ''; }
function confetti(n) {
  const box = document.body;
  for (let i = 0; i < (n || 18); i++) {
    const c = el('div', 'confetti', pick(['🎉', '⭐', '✨', pick(THEME.items)]));
    c.style.left = rand(100) + 'vw';
    c.style.animationDelay = (rng() * 0.4) + 's';
    c.style.fontSize = (22 + rand(26)) + 'px';
    box.appendChild(c);
    setTimeout(() => c.remove(), 2600);
  }
}
function praise() { const p = pick(PRAISE); speak(p); return p; }
function bigBanner(text, emoji) {
  const b = el('div', 'banner');
  b.append(el('div', 'banner-emoji', emoji || '🎉'), el('div', 'banner-text', text));
  document.body.appendChild(b);
  setTimeout(() => b.remove(), 1600);
}

/* ---------------- rounds / stars / stickers ---------------- */
let roundStars = 0;
function starWin() {
  roundStars++;
  store.totalRounds++;
  save();
  const meter = document.getElementById('stars');
  meter.textContent = '⭐'.repeat(((roundStars - 1) % 5) + 1);
  if (roundStars % 5 === 0) {
    const s = pick(STICKERS);
    store.stickers.push(s);
    save();
    sfx('sticker');
    bigBanner('New sticker!', s);
    speak('You earned a new sticker! ' + PRAISE[rand(PRAISE.length)]);
    setTimeout(() => { meter.textContent = ''; }, 1500);
  }
}
function nextRound(delay) { setTimeout(playRound, delay === undefined ? 1400 : delay); }

/* ---------------- choice grid helper ---------------- */
function choiceRound(opts) {
  // opts: {prompt, say, winSay, targetId, choices:[{label, correct}], big}
  clearStage();
  const s = stage();
  s.append(el('div', 'prompt', opts.prompt));
  const grid = el('div', 'grid cols' + Math.min(opts.choices.length, 3));
  let done = false;
  shuffle(opts.choices).forEach(ch => {
    const b = el('button', 'card ' + (opts.big ? 'big' : ''), ch.label);
    b.onclick = () => {
      if (done) return;
      if (ch.correct) {
        done = true;
        b.classList.add('right');
        sfx('yay'); confetti();
        bumpCorrect(opts.targetId);
        speak(pick(PRAISE) + ' ' + (opts.winSay || ''));
        starWin();
        nextRound();
      } else {
        b.classList.add('wrong');
        sfx('oops');
        bumpWrong(opts.targetId);
        speak(opts.say ? 'Try again! ' + opts.say : 'Try again!');
        setTimeout(() => b.classList.remove('wrong'), 600);
      }
    };
    grid.appendChild(b);
  });
  s.appendChild(grid);
  speak(opts.say || opts.prompt);
}

/* ---------------- activities ---------------- */

// 1) Meet a letter: tap the giant letter, hear it, see a word.
function actMeetLetter() {
  const L = chooseTarget(letterPool(), 'L:');
  const id = 'L:' + L;
  bumpSeen(id);
  const word = pick(LETTERS[L].words);
  clearStage();
  const s = stage();
  s.append(el('div', 'prompt', 'This is the letter ' + L + '!'));
  const glyph = el('button', 'giant', L);
  let taps = 0;
  glyph.onclick = () => {
    taps++;
    sfx('pop');
    glyph.classList.remove('bounce'); void glyph.offsetWidth; glyph.classList.add('bounce');
    if (taps === 1) speak(L + '!');
    else if (taps === 2) speak(L + ' says ' + LETTERS[L].sound + '.');
    else {
      speak(L + ' is for ' + word[0] + '!');
      const w = el('div', 'word-reveal');
      w.append(el('div', 'word-emoji', word[1]), el('div', 'word-text', L + ' is for ' + word[0]));
      s.appendChild(w);
      confetti();
      bumpCorrect(id);
      starWin();
      nextRound(2200);
    }
  };
  s.appendChild(glyph);
  s.append(el('div', 'hint', 'Tap the letter!'));
  speak('This is the letter ' + L + '! Tap it!');
}

// 2) Meet a number: tap objects one by one, counting aloud.
function actCountTap() {
  const N = parseInt(chooseTarget(numberPool(), 'N:'), 10);
  const id = 'N:' + N;
  bumpSeen(id);
  const emo = pick(THEME.items);
  clearStage();
  const s = stage();
  s.append(el('div', 'prompt', 'Tap and count to ' + N + '!'));
  const grid = el('div', 'count-grid');
  let counted = 0;
  for (let i = 0; i < N; i++) {
    const b = el('button', 'count-item', emo);
    b.onclick = () => {
      if (b.classList.contains('counted')) return;
      b.classList.add('counted');
      counted++;
      b.textContent = counted;
      sfx('pop');
      speak(String(counted), { rate: 0.95 });
      if (counted === N) {
        setTimeout(() => {
          speak(N + '! ' + N + ' ' + emo + '. ' + pick(PRAISE));
          confetti(); sfx('yay');
          bumpCorrect(id);
          starWin();
          nextRound(2000);
        }, 500);
      }
    };
    grid.appendChild(b);
  }
  s.appendChild(grid);
  const numEl = el('div', 'corner-number', String(N));
  s.appendChild(numEl);
  speak('Let\'s count to ' + N + '! Tap each one!');
}

// 3) Find the letter/number among choices.
function actFindIt(kind) {
  const isLetter = kind === 'letter';
  const pool = isLetter ? letterPool() : numberPool();
  const prefix = isLetter ? 'L:' : 'N:';
  const target = chooseTarget(pool, prefix);
  const id = prefix + target;
  const m = item(id).mastery;
  const k = m <= 1 ? 2 : m <= 3 ? 3 : 4;
  const others = shuffle(pool.filter(v => v !== target)).slice(0, k - 1);
  choiceRound({
    prompt: (isLetter ? 'Find the letter ' : 'Find the number ') + target + '!',
    say: 'Where is ' + (isLetter ? 'the letter ' : 'the number ') + target + '? Tap it!',
    winSay: 'That is ' + target + '!',
    targetId: id,
    big: true,
    choices: [{ label: target, correct: true }].concat(others.map(o => ({ label: o, correct: false }))),
  });
}

// 4) Bubble pop: pop every bubble with the target on it.
function actBubblePop(kind) {
  const isLetter = kind === 'letter';
  const pool = isLetter ? letterPool() : numberPool();
  const prefix = isLetter ? 'L:' : 'N:';
  const target = chooseTarget(pool, prefix);
  const id = prefix + target;
  clearStage();
  const s = stage();
  s.append(el('div', 'prompt', 'Pop every ' + target + '!'));
  const sky = el('div', 'sky');
  const total = 6;
  const targets = 3;
  let popped = 0;
  const labels = [];
  for (let i = 0; i < targets; i++) labels.push(target);
  const others = pool.filter(v => v !== target);
  for (let i = targets; i < total; i++) labels.push(pick(others));
  shuffle(labels).forEach((lab, i) => {
    const b = el('button', 'bubble', lab);
    b.style.left = (6 + (i % 3) * 30 + rand(8)) + '%';
    b.style.top = (8 + Math.floor(i / 3) * 40 + rand(10)) + '%';
    b.style.animationDelay = (rng() * 2) + 's';
    b.style.animationDuration = (3 + rng() * 2) + 's';
    b.onclick = () => {
      if (lab === target) {
        b.classList.add('popped');
        sfx('pop');
        popped++;
        speak(target + '!', { rate: 1 });
        if (popped === targets) {
          bumpCorrect(id);
          confetti(); sfx('yay');
          speak('You popped all the ' + target + ' bubbles! ' + pick(PRAISE));
          starWin();
          nextRound(1800);
        }
      } else {
        sfx('oops');
        bumpWrong(id);
        b.classList.add('wrong');
        speak('That is ' + lab + '. Find ' + target + '!');
        setTimeout(() => b.classList.remove('wrong'), 600);
      }
    };
    sky.appendChild(b);
  });
  s.appendChild(sky);
  speak('Pop every bubble with ' + target + ' on it!');
}

// 5) How many? Count emojis, choose the number.
function actHowMany() {
  const N = parseInt(chooseTarget(numberPool(), 'N:'), 10);
  const id = 'N:' + N;
  const emo = pick(THEME.items);
  clearStage();
  const s = stage();
  s.append(el('div', 'prompt', 'How many ' + emo + '?'));
  const pen = el('div', 'count-grid small');
  for (let i = 0; i < N; i++) pen.appendChild(el('div', 'count-show', emo));
  s.appendChild(pen);
  const opts = new Set([N]);
  while (opts.size < 3) {
    const alt = Math.max(1, N + (rand(5) - 2));
    if (alt !== N) opts.add(alt);
  }
  const grid = el('div', 'grid cols3');
  let done = false;
  shuffle([...opts]).forEach(n => {
    const b = el('button', 'card big', String(n));
    b.onclick = () => {
      if (done) return;
      if (n === N) {
        done = true;
        b.classList.add('right');
        sfx('yay'); confetti();
        bumpCorrect(id);
        speak(N + '! There are ' + N + '. ' + pick(PRAISE));
        starWin();
        nextRound();
      } else {
        b.classList.add('wrong'); sfx('oops'); bumpWrong(id);
        speak('Count again! Touch each one.');
        setTimeout(() => b.classList.remove('wrong'), 600);
      }
    };
    grid.appendChild(b);
  });
  s.appendChild(grid);
  speak('Count them! How many do you see?');
}

// 6) Match uppercase with lowercase.
function actMatchCase() {
  const L = chooseTarget(letterPool(), 'L:');
  const id = 'L:' + L;
  const others = shuffle(letterPool().filter(v => v !== L)).slice(0, 2);
  choiceRound({
    prompt: 'Find little "' + L.toLowerCase() + '" — big ' + L + '\'s baby!',
    say: 'Big ' + L + ' has a baby letter. Find the little ' + L + '!',
    winSay: 'Big ' + L + ' and little ' + L + '!',
    targetId: id,
    big: true,
    choices: [{ label: L.toLowerCase(), correct: true }].concat(others.map(o => ({ label: o.toLowerCase(), correct: false }))),
  });
  stage().appendChild(el('div', 'corner-number', L));
}

// 7) Phonics: which letter makes this sound / starts this word?
function actSoundFind() {
  const L = chooseTarget(letterPool(), 'L:');
  const id = 'L:' + L;
  const word = pick(LETTERS[L].words);
  const others = shuffle(letterPool().filter(v => v !== L)).slice(0, 2);
  clearStage();
  const s = stage();
  s.append(el('div', 'prompt', word[1] + ' ' + word[0] + ' starts with...?'));
  const grid = el('div', 'grid cols3');
  let done = false;
  shuffle([L].concat(others)).forEach(cand => {
    const b = el('button', 'card big', cand);
    b.onclick = () => {
      if (done) return;
      if (cand === L) {
        done = true; b.classList.add('right'); sfx('yay'); confetti();
        bumpCorrect(id);
        speak(L + '! ' + LETTERS[L].sound + ' for ' + word[0] + '! ' + pick(PRAISE));
        starWin();
        nextRound();
      } else {
        b.classList.add('wrong'); sfx('oops'); bumpWrong(id);
        speak('Listen: ' + LETTERS[L].sound + ', ' + word[0] + '. Which letter?');
        setTimeout(() => b.classList.remove('wrong'), 600);
      }
    };
    grid.appendChild(b);
  });
  s.appendChild(grid);
  speak(word[0] + '! ' + LETTERS[L].sound + ', ' + word[0] + '. Which letter says ' + LETTERS[L].sound + '?');
}

// 8) What comes next? (sequences)
function actWhatsNext(kind) {
  const isLetter = kind === 'letter';
  let seq, answer, id;
  if (isLetter) {
    const abc = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    const st = rand(24);
    seq = [abc[st], abc[st + 1]];
    answer = abc[st + 2];
    id = 'L:' + answer;
  } else {
    const max = numberPool().length;
    const st = 1 + rand(Math.max(1, max - 2));
    seq = [String(st), String(st + 1)];
    answer = String(st + 2);
    id = 'N:' + answer;
  }
  const wrongs = new Set();
  const abc = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  while (wrongs.size < 2) {
    const w = isLetter ? abc[rand(26)] : String(1 + rand(numberPool().length));
    if (w !== answer && !seq.includes(w)) wrongs.add(w);
  }
  clearStage();
  const s = stage();
  s.append(el('div', 'prompt', 'What comes next?'));
  const row = el('div', 'seq-row');
  seq.forEach(v => row.appendChild(el('div', 'seq-item', v)));
  row.appendChild(el('div', 'seq-item blank', '?'));
  s.appendChild(row);
  const grid = el('div', 'grid cols3');
  let done = false;
  shuffle([answer, ...wrongs]).forEach(cand => {
    const b = el('button', 'card big', cand);
    b.onclick = () => {
      if (done) return;
      if (cand === answer) {
        done = true; b.classList.add('right');
        row.lastChild.textContent = answer;
        row.lastChild.classList.remove('blank');
        sfx('yay'); confetti();
        bumpCorrect(id);
        speak(seq[0] + ', ' + seq[1] + ', ' + answer + '! ' + pick(PRAISE));
        starWin();
        nextRound(1800);
      } else {
        b.classList.add('wrong'); sfx('oops'); bumpWrong(id);
        speak(seq[0] + ', ' + seq[1] + '... what comes next?');
        setTimeout(() => b.classList.remove('wrong'), 600);
      }
    };
    grid.appendChild(b);
  });
  s.appendChild(grid);
  speak(seq.join(', ') + '... what comes next?');
}

// 9) Build a word: tap its letters in order.
function actWordBuild() {
  const [word, emoji, sentence] = pick(WORDS);
  const id = 'W:' + word;
  bumpSeen(id);
  clearStage();
  const s = stage();
  s.append(el('div', 'prompt', 'Build the word: ' + word + ' ' + emoji));
  const slots = el('div', 'seq-row');
  const slotEls = [...word].map(() => { const d = el('div', 'seq-item blank', '_'); slots.appendChild(d); return d; });
  s.appendChild(slots);
  const letters = shuffle([...word].concat(shuffle('ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').filter(c => !word.includes(c))).slice(0, 2)));
  const grid = el('div', 'grid cols3');
  let idx = 0;
  letters.forEach(ch => {
    const b = el('button', 'card', ch);
    b.onclick = () => {
      if (b.classList.contains('used')) return;
      if (ch === word[idx]) {
        b.classList.add('used');
        slotEls[idx].textContent = ch;
        slotEls[idx].classList.remove('blank');
        sfx('pop');
        speak(ch + '!', { rate: 1.05 });
        idx++;
        if (idx === word.length) {
          sfx('yay'); confetti(24);
          bumpCorrect(id);
          speak(word.split('').join(', ') + ' spells ' + word + '! ' + sentence);
          starWin();
          nextRound(2600);
        }
      } else {
        b.classList.add('wrong'); sfx('oops');
        speak('We need ' + word[idx] + ' next!');
        setTimeout(() => b.classList.remove('wrong'), 600);
      }
    };
    grid.appendChild(b);
  });
  s.appendChild(grid);
  speak('Let\'s build the word ' + word + '! Find ' + word[0] + ' first!');
}

// 10) More or less (number tier 4).
function actMoreLess() {
  const emoA = pick(THEME.items);
  let emoB = pick(THEME.items);
  while (emoB === emoA) emoB = pick(THEME.items);
  let a = 1 + rand(9), b = 1 + rand(9);
  while (a === b) b = 1 + rand(9);
  const wantMore = rng() > 0.5;
  const answer = wantMore ? Math.max(a, b) : Math.min(a, b);
  const id = 'N:' + answer;
  clearStage();
  const s = stage();
  s.append(el('div', 'prompt', 'Which side has ' + (wantMore ? 'MORE' : 'LESS') + '?'));
  const grid = el('div', 'grid cols2');
  let done = false;
  [[a, emoA], [b, emoB]].forEach(([n, emo]) => {
    const b2 = el('button', 'card pen');
    for (let i = 0; i < n; i++) b2.appendChild(el('span', 'mini', emo));
    b2.onclick = () => {
      if (done) return;
      if (n === answer) {
        done = true; b2.classList.add('right'); sfx('yay'); confetti();
        bumpCorrect(id);
        speak(n + ' is ' + (wantMore ? 'more' : 'less') + '! ' + pick(PRAISE));
        starWin();
        nextRound();
      } else {
        b2.classList.add('wrong'); sfx('oops'); bumpWrong(id);
        speak('Count each side. Which has ' + (wantMore ? 'more' : 'less') + '?');
        setTimeout(() => b2.classList.remove('wrong'), 600);
      }
    };
    grid.appendChild(b2);
  });
  s.appendChild(grid);
  speak('Which side has ' + (wantMore ? 'more' : 'less') + '? Tap it!');
}

/* ---------------- round scheduler ---------------- */
function activitiesForNow() {
  const lt = letterTier(), nt = numberTier();
  const acts = [];
  // Letters
  acts.push(['meetLetter', actMeetLetter, 3]);
  acts.push(['findLetter', () => actFindIt('letter'), 3]);
  acts.push(['bubbleLetter', () => actBubblePop('letter'), 2]);
  if (lt >= 2) acts.push(['matchCase', actMatchCase, 2]);
  if (lt >= 3) acts.push(['soundFind', actSoundFind, 2]);
  if (lt >= 3) acts.push(['nextLetter', () => actWhatsNext('letter'), 1]);
  if (lt >= 4) acts.push(['wordBuild', actWordBuild, 3]);
  // Numbers
  acts.push(['countTap', actCountTap, 3]);
  acts.push(['findNumber', () => actFindIt('number'), 2]);
  acts.push(['howMany', actHowMany, 2]);
  if (nt >= 2) acts.push(['bubbleNumber', () => actBubblePop('number'), 2]);
  if (nt >= 3) acts.push(['nextNumber', () => actWhatsNext('number'), 2]);
  if (nt >= 4) acts.push(['moreLess', actMoreLess, 2]);
  return acts;
}
let lastAct = '';
function playRound() {
  const acts = activitiesForNow();
  const weighted = [];
  acts.forEach(([name, fn, w]) => { if (name !== lastAct) for (let i = 0; i < w; i++) weighted.push([name, fn]); });
  const [name, fn] = pick(weighted);
  lastAct = name;
  fn();
}

/* ---------------- sticker book (show friends!) ---------------- */
function showStickers() {
  clearStage();
  const s = stage();
  s.append(el('div', 'prompt', 'My Sticker Book! 🏆'));
  const learned = Object.keys(store.items).filter(id => store.items[id].mastery >= MASTERED);
  const board = el('div', 'sticker-board');
  if (!store.stickers.length) board.append(el('div', 'hint', 'Play to earn stickers!'));
  store.stickers.forEach(st => board.append(el('div', 'sticker', st)));
  s.appendChild(board);
  s.append(el('div', 'hint', 'I know ' + learned.filter(i => i.startsWith('L:')).length + ' letters and ' +
    learned.filter(i => i.startsWith('N:')).length + ' numbers!'));
  const back = el('button', 'card', '▶️ Keep playing!');
  back.onclick = () => playRound();
  s.appendChild(back);
  speak('Look at all my stickers! I earned ' + store.stickers.length + '!');
}

/* ---------------- parent gate ---------------- */
function setupParentGate() {
  const btn = document.getElementById('parents-link');
  let timer = null;
  const go = () => { location.href = 'parents.html'; };
  const start = (e) => {
    e.preventDefault();
    btn.classList.add('holding');
    timer = setTimeout(go, 2000);
  };
  const stop = () => { btn.classList.remove('holding'); if (timer) clearTimeout(timer); };
  btn.addEventListener('pointerdown', start);
  btn.addEventListener('pointerup', stop);
  btn.addEventListener('pointerleave', stop);
}

/* ---------------- boot ---------------- */
window.addEventListener('DOMContentLoaded', () => {
  document.documentElement.style.setProperty('--bg1', THEME.bg[0]);
  document.documentElement.style.setProperty('--bg2', THEME.bg[1]);
  document.documentElement.style.setProperty('--accent', THEME.accent);
  document.getElementById('mascot').textContent = THEME.mascot;
  document.getElementById('theme-name').textContent = THEME.name;
  document.getElementById('sticker-btn').onclick = showStickers;
  setupParentGate();
  // Start screen: one big tap unlocks audio (mobile requirement) then plays.
  const s = stage();
  const startBtn = el('button', 'giant start', '▶');
  const title = el('div', 'prompt', THEME.mascot + ' ' + THEME.name + ' — tap to play!');
  s.append(title, startBtn);
  startBtn.onclick = () => {
    ctx();
    speak('Hello! Welcome to ' + THEME.name + '! Let\'s play!');
    sfx('yay');
    setTimeout(playRound, 1200);
  };
});
