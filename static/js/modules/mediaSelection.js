export function setupMediaSelection() {
  const mediaButtons = document.querySelectorAll(".media-buttons button");
  const mediaTypeInput = document.getElementById("media-type");

  mediaButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      mediaButtons.forEach(b => b.classList.remove("selected"));
      btn.classList.add("selected");
      mediaTypeInput.value = btn.dataset.type;
    });
  });
}