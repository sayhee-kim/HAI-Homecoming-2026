const state = {
  people: [],
  answer: null,
  round: 0,
  scores: new Map(),
  roundStartedAt: performance.now(),
  roundClosed: false,
  answerRevealed: false,
};

const excludedQuizNames = new Set(["최중명", "이찬", "박준호", "최종현", "박승영", "왕박락"]);

const stage = document.querySelector("#stage");
const segments = {
  brow: document.querySelector("#segmentBrow"),
  eyes: document.querySelector("#segmentEyes"),
  nose: document.querySelector("#segmentNose"),
  mouth: document.querySelector("#segmentMouth"),
};
const hints = {
  brow: document.querySelector("#hintBrow"),
  eyes: document.querySelector("#hintEyes"),
  nose: document.querySelector("#hintNose"),
  mouth: document.querySelector("#hintMouth"),
};
const speedRange = document.querySelector("#speedRange");
const winnerInput = document.querySelector("#winnerInput");
const playerNames = document.querySelector("#playerNames");
const awardButton = document.querySelector("#awardButton");
const voidButton = document.querySelector("#voidButton");
const endButton = document.querySelector("#endButton");
const revealButton = document.querySelector("#revealButton");
const scoreChart = document.querySelector("#scoreChart");
const result = document.querySelector("#result");
const resultImage = document.querySelector("#resultImage");
const resultState = document.querySelector("#resultState");
const resultName = document.querySelector("#resultName");
const resultRole = document.querySelector("#resultRole");
const nextButton = document.querySelector("#nextButton");
const roundLabel = document.querySelector("#roundLabel");
const scoreLabel = document.querySelector("#scoreLabel");

const shuffle = (items) => {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
};

const speedDuration = () => 22 - Number(speedRange.value);

const setSpeed = () => {
  stage.style.setProperty("--speed", `${speedDuration()}s`);
  syncSegments();
};

const syncSegments = () => {
  const elapsed = (performance.now() - state.roundStartedAt) / 1000;
  const delay = -(elapsed % speedDuration());
  Object.values(segments).forEach((segment) => {
    segment.style.animationDelay = `${delay}s`;
  });
};

const setSegmentImage = (person) => {
  const cuts = person.segments || {
    brow: [0, 0.28],
    eyes: [0.28, 0.39],
    nose: [0.39, 0.57],
    mouth: [0.57, 0.84],
  };

  Object.entries(segments).forEach(([key, segment]) => {
    const [top, bottom] = cuts[key];
    segment.style.backgroundImage = `url("${person.image}")`;
    segment.style.top = `calc(50% - var(--face-height) / 2 + var(--face-height) * ${top})`;
    segment.style.height = `calc(var(--face-height) * ${bottom - top})`;
    segment.style.backgroundPositionY = `calc(var(--face-height) * -${top})`;
    segment.style.animation = "none";
    segment.offsetHeight;
    segment.style.animation = "";
  });
  syncSegments();
};

const updateHints = () => {
  syncSegments();
  Object.entries(hints).forEach(([key, input]) => {
    segments[key].classList.toggle("active", input.checked);
  });
};

const totalScore = () => [...state.scores.values()].reduce((sum, score) => sum + score, 0);

const sortedScores = () =>
  [...state.scores.entries()].sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0], "ko"));

const renderScores = () => {
  const rows = sortedScores();
  scoreLabel.textContent = totalScore();
  scoreChart.replaceChildren();

  if (rows.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-chart";
    empty.textContent = "아직 등록된 정답자가 없습니다.";
    scoreChart.appendChild(empty);
    return;
  }

  const maxScore = Math.max(...rows.map(([, score]) => score));
  rows.forEach(([name, score], index) => {
    const row = document.createElement("div");
    row.className = "score-row";
    if (index < 5) row.classList.add("top-rank");

    const rank = document.createElement("span");
    rank.className = "rank";
    rank.textContent = `${index + 1}`;

    const nameEl = document.createElement("strong");
    nameEl.textContent = name;

    const barWrap = document.createElement("div");
    barWrap.className = "bar-wrap";
    const bar = document.createElement("div");
    bar.className = "bar";
    bar.style.width = `${Math.max((score / maxScore) * 100, 12)}%`;
    barWrap.appendChild(bar);

    const scoreEl = document.createElement("span");
    scoreEl.className = "points";
    scoreEl.textContent = `${score}`;

    row.append(rank, nameEl, barWrap, scoreEl);
    scoreChart.appendChild(row);
  });
};

const showAnswer = (label) => {
  state.answerRevealed = true;
  result.hidden = false;
  resultImage.src = state.answer.image;
  resultImage.alt = `${state.answer.name} 사진`;
  resultState.textContent = label;
  resultName.textContent = state.answer.name;
  resultRole.textContent = state.answer.role;
  updateJudgeButtons();
};

const closeRound = (label) => {
  state.roundClosed = true;
  showAnswer(label);
};

const updateJudgeButtons = () => {
  const canJudge = state.answerRevealed && !state.roundClosed;
  awardButton.disabled = !canJudge;
  voidButton.disabled = !canJudge;
  revealButton.disabled = state.answerRevealed || state.roundClosed;
};

const awardPoint = () => {
  if (state.roundClosed || !state.answerRevealed) return;
  const name = winnerInput.value.trim();
  if (!name) {
    winnerInput.focus();
    return;
  }
  state.scores.set(name, (state.scores.get(name) || 0) + 1);
  winnerInput.value = "";
  renderScores();
  closeRound("이번 정답");
};

const voidRound = () => {
  if (state.roundClosed || !state.answerRevealed) return;
  winnerInput.value = "";
  closeRound("무효 처리");
};

const revealAnswer = () => {
  if (state.roundClosed || state.answerRevealed) return;
  showAnswer("정답 확인");
};

const timestamp = () => {
  const now = new Date();
  const pad = (value) => String(value).padStart(2, "0");
  return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}`;
};

const endGame = () => {
  const topFive = sortedScores().slice(0, 5);
  const title = timestamp();
  const lines = [
    `HAI Homecoming Face Quiz TOP 5`,
    title,
    "",
    ...topFive.map(([name, score], index) => `${index + 1}. ${name} - ${score}`),
  ];
  const blob = new Blob([`${lines.join("\n")}\n`], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${title}_top5.txt`;
  link.click();
  URL.revokeObjectURL(url);
};

const nextRound = () => {
  if (state.people.length === 0) {
    scoreChart.textContent = "사람 데이터가 부족합니다. 먼저 사진을 수집해 주세요.";
    return;
  }

  state.round += 1;
  state.roundClosed = false;
  state.answerRevealed = false;
  state.roundStartedAt = performance.now();
  result.hidden = true;
  winnerInput.value = "";

  state.answer = shuffle(state.people)[0];
  hints.brow.checked = true;
  hints.eyes.checked = false;
  hints.nose.checked = false;
  hints.mouth.checked = false;

  setSegmentImage(state.answer);
  updateHints();
  updateJudgeButtons();
  roundLabel.textContent = `Round ${state.round}`;
};

Object.values(hints).forEach((input) => input.addEventListener("change", updateHints));
speedRange.addEventListener("input", setSpeed);
nextButton.addEventListener("click", nextRound);
awardButton.addEventListener("click", awardPoint);
voidButton.addEventListener("click", voidRound);
endButton.addEventListener("click", endGame);
revealButton.addEventListener("click", revealAnswer);
winnerInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") awardPoint();
});

fetch("people.json")
  .then((response) => response.json())
  .then((people) => {
    state.people = people.filter((person) => person.image && !excludedQuizNames.has(person.name));
    playerNames.replaceChildren(
      ...state.people.map((person) => {
        const option = document.createElement("option");
        option.value = person.name;
        return option;
      }),
    );
    setSpeed();
    renderScores();
    nextRound();
  })
  .catch(() => {
    scoreChart.textContent = "people.json을 불러오지 못했습니다. 수집 스크립트를 먼저 실행해 주세요.";
  });
