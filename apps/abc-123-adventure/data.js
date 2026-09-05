/* ABC & 123 Adventure — content data */
'use strict';

// Letters in a toddler-friendly teaching order (SATPIN-style phonics order).
const LETTER_ORDER = ['S','A','T','P','I','N','M','D','G','O','C','K','E','R','U','B','F','L','J','H','W','V','X','Y','Z','Q'];

// Each letter: phonic sound hint + several example words (rotated for variety).
const LETTERS = {
  A: { sound: 'ah', words: [['apple','🍎'],['ant','🐜'],['airplane','✈️']] },
  B: { sound: 'buh', words: [['ball','⚽'],['banana','🍌'],['bear','🐻']] },
  C: { sound: 'kuh', words: [['cat','🐱'],['car','🚗'],['cake','🎂']] },
  D: { sound: 'duh', words: [['dog','🐶'],['duck','🦆'],['drum','🥁']] },
  E: { sound: 'eh', words: [['egg','🥚'],['elephant','🐘'],['ear','👂']] },
  F: { sound: 'fff', words: [['fish','🐟'],['frog','🐸'],['flower','🌸']] },
  G: { sound: 'guh', words: [['goat','🐐'],['grapes','🍇'],['gift','🎁']] },
  H: { sound: 'hhh', words: [['hat','🎩'],['horse','🐴'],['house','🏠']] },
  I: { sound: 'ih', words: [['igloo','🧊'],['insect','🐞'],['ice cream','🍦']] },
  J: { sound: 'juh', words: [['juice','🧃'],['jet','🛩️'],['jam','🍓']] },
  K: { sound: 'kuh', words: [['kite','🪁'],['key','🔑'],['koala','🐨']] },
  L: { sound: 'lll', words: [['lion','🦁'],['leaf','🍃'],['lemon','🍋']] },
  M: { sound: 'mmm', words: [['moon','🌙'],['monkey','🐵'],['milk','🥛']] },
  N: { sound: 'nnn', words: [['nest','🪺'],['nose','👃'],['night','🌃']] },
  O: { sound: 'oh', words: [['orange','🍊'],['owl','🦉'],['octopus','🐙']] },
  P: { sound: 'puh', words: [['pig','🐷'],['pizza','🍕'],['penguin','🐧']] },
  Q: { sound: 'kwuh', words: [['queen','👑'],['quilt','🛏️'],['question','❓']] },
  R: { sound: 'rrr', words: [['rainbow','🌈'],['rabbit','🐰'],['rocket','🚀']] },
  S: { sound: 'sss', words: [['sun','☀️'],['star','⭐'],['snake','🐍']] },
  T: { sound: 'tuh', words: [['tree','🌳'],['tiger','🐯'],['train','🚂']] },
  U: { sound: 'uh', words: [['umbrella','☂️'],['unicorn','🦄'],['up','⬆️']] },
  V: { sound: 'vvv', words: [['violin','🎻'],['volcano','🌋'],['van','🚐']] },
  W: { sound: 'wuh', words: [['whale','🐋'],['water','💧'],['watch','⌚']] },
  X: { sound: 'ks', words: [['box','📦'],['fox','🦊'],['xylophone','🎵']] },
  Y: { sound: 'yuh', words: [['yo-yo','🪀'],['yarn','🧶'],['yellow','💛']] },
  Z: { sound: 'zzz', words: [['zebra','🦓'],['zoo','🦒'],['zipper','🤐']] },
};

const NUMBER_MAX = 20;
const NUMBER_WORDS = ['zero','one','two','three','four','five','six','seven','eight','nine','ten',
  'eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen','eighteen','nineteen','twenty'];

// First sight words (tier 4 letters): word, emoji, spoken sentence.
const WORDS = [
  ['CAT','🐱','The cat says meow!'],
  ['DOG','🐶','The dog says woof!'],
  ['SUN','☀️','The sun is bright!'],
  ['BUS','🚌','The bus goes beep beep!'],
  ['HAT','🎩','A hat for your head!'],
  ['CUP','🥤','Drink from the cup!'],
  ['BED','🛏️','Time for bed!'],
  ['PIG','🐷','The pig says oink!'],
  ['MOM','🤱','I love my mom!'],
  ['DAD','👨','I love my dad!'],
  ['BIG','🐘','The elephant is big!'],
  ['RED','🔴','Red like a fire truck!'],
];

// Session themes: every session gets a random theme so it always feels new.
const THEMES = [
  { name: 'Jungle Friends', mascot: '🐵', bg: ['#daf5d0','#8fd67a'], accent: '#2e7d32', items: ['🐵','🦁','🐘','🦜','🐍','🦋'] },
  { name: 'Ocean Splash',  mascot: '🐬', bg: ['#d0ecf5','#7ac4d6'], accent: '#0277bd', items: ['🐬','🐟','🐙','🦀','🐳','⭐'] },
  { name: 'Space Trip',    mascot: '🚀', bg: ['#e0d9f7','#a08fe0'], accent: '#5e35b1', items: ['🚀','⭐','🌙','🪐','👽','☄️'] },
  { name: 'Farm Day',      mascot: '🐮', bg: ['#f7efd0','#e0c878'], accent: '#a06e12', items: ['🐮','🐷','🐔','🐑','🦆','🌻'] },
  { name: 'Fruit Party',   mascot: '🍓', bg: ['#fbe0e8','#f29ab5'], accent: '#c2185b', items: ['🍓','🍌','🍎','🍇','🍉','🍊'] },
  { name: 'Busy Cars',     mascot: '🚗', bg: ['#dbe7f5','#93b6e0'], accent: '#1565c0', items: ['🚗','🚌','🚒','🚜','🚂','✈️'] },
  { name: 'Dino Land',     mascot: '🦕', bg: ['#e2f5d0','#a8d67a'], accent: '#558b2f', items: ['🦕','🦖','🥚','🌋','🌴','🦴'] },
  { name: 'Snowy Fun',     mascot: '⛄', bg: ['#e6f2fa','#a9d3ee'], accent: '#0288d1', items: ['⛄','❄️','🐧','🧤','🛷','🌨️'] },
  { name: 'Bug Garden',    mascot: '🐞', bg: ['#eef7d0','#c3e07a'], accent: '#7b8d1a', items: ['🐞','🦋','🐝','🐛','🐌','🌼'] },
  { name: 'Music Time',    mascot: '🎵', bg: ['#f5e0d0','#e0a97a'], accent: '#bf5f1f', items: ['🎵','🥁','🎺','🎹','🎸','🎻'] },
];

const PRAISE = ['Yay!','Wow!','Great job!','You did it!','Amazing!','Super!','Hooray!','Fantastic!','High five!','Brilliant!'];
const STICKERS = ['🌟','🏆','🎈','🦄','🌈','🍭','🧸','🎁','💎','👑','🪁','🛸','🎠','🍩','🐣','🌻'];
