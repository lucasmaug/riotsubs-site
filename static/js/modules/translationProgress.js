export function setupTranslationProgress() {
  const stepOptions = document.getElementById("step-options");
  const stepProgress = document.getElementById("step-progress");
  const stepFinal = document.getElementById("step-final");
  const progressFill = document.getElementById("progress-fill");

  document.getElementById("translate-form").addEventListener("submit", e => {
    e.preventDefault();
    stepOptions.classList.add("hidden");
    stepProgress.classList.remove("hidden");

    let progress = 0;
    const interval = setInterval(() => {
      if (progress < 100) {
        progress += 1;
        progressFill.style.width = progress + "%";
        progressFill.textContent = progress + "%";
      } else {
        clearInterval(interval);
        progressFill.style.width = "100%";
        progressFill.textContent = "100%";
        stepProgress.classList.add("hidden");
        stepFinal.classList.remove("hidden");
      }
    }, 40);
  });

  document.getElementById("cancel-progress").addEventListener("click", () => {
    location.reload();
  });

  document.getElementById("restart-process").addEventListener("click", () => {
    location.reload();
  });
}