export function setupNavigation() {
  const stepUpload  = document.getElementById('step-upload');
  const stepOptions = document.getElementById('step-options');

  document.getElementById('next-to-options').addEventListener('click', () => {
    stepUpload.classList.add('hidden');
    stepOptions.classList.remove('hidden');
  });

  document.getElementById('back-to-upload').addEventListener('click', () => {
    stepOptions.classList.add('hidden');
    stepUpload.classList.remove('hidden');
  });
}