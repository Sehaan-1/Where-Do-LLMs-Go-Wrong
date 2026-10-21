"use strict";

const sampleResponse = {
  question:
    "Janet’s ducks lay 16 eggs per day. She eats three for breakfast every morning and bakes muffins for her friends every day with four. She sells the remainder at the farmers' market daily for $2 per fresh duck egg. How much in dollars does she make every day at the farmers' market?",
  referenceAnswer: "18",
  steps: [
    "Janet eats 3 ducks eggs for breakfast every morning and she sells the rest so she has 16 - 3 = <<16-3=13>>13 ducks eggs left",
    "She has 13 ducks eggs and she sells 2 each day so she makes 13 * 2 = $<<13*2=26>>26",
    "A: 26",
  ],
};

const priorElement = document.querySelector("#sample-prior");
const currentElement = document.querySelector("#sample-current");
const followingElement = document.querySelector("#sample-following");
const positionElement = document.querySelector("#preview-position");
const questionElement = document.querySelector("#sample-question");
const answerElement = document.querySelector("#sample-answer");
const previousButton = document.querySelector("#previous-line");
const nextButton = document.querySelector("#next-line");
const previewControls = document.querySelector(".task-control-buttons");

if (
  priorElement instanceof HTMLElement &&
  currentElement instanceof HTMLElement &&
  followingElement instanceof HTMLElement &&
  positionElement instanceof HTMLElement &&
  questionElement instanceof HTMLElement &&
  answerElement instanceof HTMLElement &&
  previousButton instanceof HTMLButtonElement &&
  nextButton instanceof HTMLButtonElement &&
  previewControls instanceof HTMLElement
) {
  previewControls.hidden = false;
  questionElement.textContent = sampleResponse.question;
  answerElement.textContent = sampleResponse.referenceAnswer;

  let currentIndex = 0;

  const renderSampleStep = () => {
    const priorSteps = sampleResponse.steps.slice(0, currentIndex);
    const followingSteps = sampleResponse.steps.slice(currentIndex + 1);
    priorElement.textContent = priorSteps.length
      ? priorSteps.join("\n")
      : "No earlier lines in this response.";
    currentElement.textContent = sampleResponse.steps[currentIndex];
    followingElement.textContent = followingSteps.length
      ? followingSteps.join("\n")
      : "No later lines in this response.";
    positionElement.textContent =
      `Source line ${currentIndex + 1} of ${sampleResponse.steps.length}. No label is selected.`;
    previousButton.disabled = currentIndex === 0;
    nextButton.disabled = currentIndex === sampleResponse.steps.length - 1;
  };

  previousButton.addEventListener("click", () => {
    currentIndex = Math.max(0, currentIndex - 1);
    renderSampleStep();
  });
  nextButton.addEventListener("click", () => {
    currentIndex = Math.min(sampleResponse.steps.length - 1, currentIndex + 1);
    renderSampleStep();
  });
  renderSampleStep();
}

const workflowStages = [
  {
    title: "Pinned source",
    copy: "The batch comes from one recorded GSM8K revision. Preparation makes no model API calls.",
    facts: [
      ["Source rows", "1,319"],
      ["Source revision", "3101c7d"],
      ["Model API calls", "None"],
    ],
  },
  {
    title: "Deterministic seed",
    copy: "A reproducible sample keeps both historical response conditions for each selected problem.",
    facts: [
      ["Sampling seed", "2026"],
      ["Paired problems", "150"],
      ["Responses", "300"],
    ],
  },
  {
    title: "Human annotation",
    copy: "Independent review is the next research step. The current seed has not been human-labeled.",
    facts: [
      ["Labels collected", "0"],
      ["Double-coded sample", "30 problems"],
      ["Step tasks in sample", "265"],
    ],
  },
  {
    title: "Agreement and analysis",
    copy: "Reports are computed only after validated, independent annotations are supplied.",
    facts: [
      ["Cohen’s kappa", "Pending"],
      ["First-error findings", "Pending"],
      ["Current report", "Pre-annotation"],
    ],
  },
];

const workflowControls = document.querySelector("#workflow-controls");
const stageRange = document.querySelector("#workflow-stage");
const stageTitle = document.querySelector("#workflow-stage-title");
const stageCopy = document.querySelector("#workflow-stage-copy");
const stageCount = document.querySelector("#workflow-count");

if (
  workflowControls instanceof HTMLElement &&
  stageRange instanceof HTMLInputElement &&
  stageTitle instanceof HTMLElement &&
  stageCopy instanceof HTMLElement &&
  stageCount instanceof HTMLElement
) {
  workflowControls.hidden = false;
  const factLabels = [1, 2, 3].map((index) =>
    document.querySelector(`#workflow-fact-label-${index}`),
  );
  const factValues = [1, 2, 3].map((index) =>
    document.querySelector(`#workflow-fact-value-${index}`),
  );

  const renderWorkflowStage = () => {
    const stageIndex = Number(stageRange.value);
    const stage = workflowStages[stageIndex];
    if (!stage) return;

    stageRange.setAttribute("aria-valuetext", stage.title);
    stageTitle.textContent = stage.title;
    stageCopy.textContent = stage.copy;
    stageCount.textContent = `Stage ${stageIndex + 1} of ${workflowStages.length}`;

    stage.facts.forEach(([label, value], index) => {
      const labelElement = factLabels[index];
      const valueElement = factValues[index];
      if (labelElement instanceof HTMLElement && valueElement instanceof HTMLElement) {
        labelElement.textContent = label;
        valueElement.textContent = value;
      }
    });
  };

  stageRange.addEventListener("input", renderWorkflowStage);
  renderWorkflowStage();
}
