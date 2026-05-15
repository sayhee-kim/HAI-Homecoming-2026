const state = {
  people: [],
  answer: null,
  choices: [],
  round: 0,
  score: 0,
  locked: false,
};

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
const choicesEl = document.querySelector("#choices");
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

const sample = (items, count, excluded) =>
  shuffle(items.filter((item) => item !== excluded)).slice(0, count);

const setSpeed = () => {
  const value = Number(speedRange.value);
  stage.style.setProperty("--speed", `${22 - value}s`);
};

const setSegmentImage = (person) => {
  const cuts = person.segments || {
    brow: [0.17, 0.28],
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
};

const updateHints = () => {
  Object.entries(hints).forEach(([key, input]) => {
    segments[key].classList.toggle("active", input.checked);
  });
};

const renderChoices = () => {
  choicesEl.replaceChildren();
  state.choices.forEach((person) => {
    const button = document.createElement("button");
    button.className = "choice";
    button.type = "button";
    button.textContent = person.name;
    button.addEventListener("click", () => choose(person, button));
    choicesEl.appendChild(button);
  });
};

const choose = (person, button) => {
  if (state.locked) return;
  state.locked = true;

  const isCorrect = person === state.answer;
  if (isCorrect) state.score += 1;
  scoreLabel.textContent = state.score;

  document.querySelectorAll(".choice").forEach((choice) => {
    const isAnswer = choice.textContent === state.answer.name;
    choice.classList.toggle("correct", isAnswer);
    choice.disabled = true;
  });
  if (!isCorrect) button.classList.add("wrong");

  result.hidden = false;
  resultImage.src = state.answer.image;
  resultImage.alt = `${state.answer.name} 사진`;
  resultState.textContent = isCorrect ? "정답!" : "아쉽습니다";
  resultName.textContent = state.answer.name;
  resultRole.textContent = state.answer.role;
};

const nextRound = () => {
  if (state.people.length < 4) {
    choicesEl.textContent = "사람 데이터가 부족합니다. 먼저 사진을 수집해 주세요.";
    return;
  }

  state.round += 1;
  state.locked = false;
  result.hidden = true;

  state.answer = shuffle(state.people)[0];
  state.choices = shuffle([state.answer, ...sample(state.people, 3, state.answer)]);

  hints.brow.checked = true;
  hints.eyes.checked = false;
  hints.nose.checked = false;
  hints.mouth.checked = false;

  setSegmentImage(state.answer);
  updateHints();
  renderChoices();
  roundLabel.textContent = `Round ${state.round}`;
};

Object.values(hints).forEach((input) => input.addEventListener("change", updateHints));
speedRange.addEventListener("input", setSpeed);
nextButton.addEventListener("click", nextRound);

fetch("people.json")
  .then((response) => response.json())
  .then((people) => {
    state.people = people.filter((person) => person.image);
    setSpeed();
    nextRound();
  })
  .catch(() => {
    choicesEl.textContent = "people.json을 불러오지 못했습니다. 수집 스크립트를 먼저 실행해 주세요.";
  });
