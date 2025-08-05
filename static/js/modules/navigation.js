export function setupNavigation() {
  const nextToOptions = document.getElementById("next-to-options");
  const stepUpload = document.getElementById("step-upload");
  const stepOptions = document.getElementById("step-options");
  const stepProgress = document.getElementById("step-progress");
  const stepFinal = document.getElementById("step-final");

  nextToOptions.addEventListener("click", () => {
    stepUpload.classList.add("hidden");
    stepOptions.classList.remove("hidden");
  });

  function goBack() {
    stepOptions.classList.add("hidden");
    stepUpload.classList.remove("hidden");
  }

  return { goBack };
}