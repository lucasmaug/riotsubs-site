// Mapa de sufixos por código de idioma
const LANG_SUFFIX = {
  'pt-br': '-pt-br',
  'pt-pt': '-pt-pt',
  'en':    '-en',
  'es':    '-es',
};

// Gera o nome do arquivo de saída com base no nome original e no idioma
export function buildOutputFilename(originalName, langCode) {
  const suffix = LANG_SUFFIX[langCode] || '';
  const dotIndex = originalName.lastIndexOf('.');
  if (dotIndex === -1) return originalName + suffix;
  const base = originalName.slice(0, dotIndex);
  const ext  = originalName.slice(dotIndex); // inclui o ponto
  return base + suffix + ext;
}

// Atualiza a prévia do nome do arquivo nas etapas 1 e 4
function refreshFilenamePreview() {
  const fileUpload = document.getElementById('file-upload');
  const langSelect = document.getElementById('lang');
  if (!fileUpload?.files[0]) return;

  const langCode  = langSelect?.value || '';
  const outputName = buildOutputFilename(fileUpload.files[0].name, langCode);

  const fileNameDisplay = document.getElementById('file-name');
  const fileNameFinal   = document.getElementById('file-name-final');
  if (fileNameDisplay) fileNameDisplay.textContent = outputName;
  if (fileNameFinal)   fileNameFinal.textContent   = outputName;
}

// Configura os listeners de eventos para a interface
export function setupFileUpload() {
  const fileUpload      = document.getElementById('file-upload');
  const fileInfo        = document.getElementById('file-info');
  const fileNameDisplay = document.getElementById('file-name');
  const uploadBtn       = document.getElementById('upload-btn');
  const langSelect      = document.getElementById('lang');
  const submitBtn       = document.getElementById('submit-btn');

  // Habilita o botão de traduzir só quando idioma for escolhido
  langSelect?.addEventListener('change', () => {
    if (submitBtn) {
      submitBtn.disabled = !langSelect.value;
    }
    refreshFilenamePreview();
  });

  // Clique no botão de upload
  uploadBtn.addEventListener('click', () => fileUpload.click());

  // Quando o usuário seleciona um arquivo
  fileUpload.addEventListener('change', () => {
    const file = fileUpload.files[0];
    if (!file) return;

    document.getElementById('upload-box').classList.add('hidden');
    fileInfo.classList.remove('hidden');
    refreshFilenamePreview();
  });

  // Botão "Substituir arquivo"
  document.getElementById('replace-file').addEventListener('click', () => {
    fileUpload.value = '';
    fileInfo.classList.add('hidden');
    if (fileNameDisplay) fileNameDisplay.textContent = '';
    document.getElementById('upload-box').classList.remove('hidden');

    const downloadLink = document.getElementById('download-link');
    if (downloadLink && !downloadLink.classList.contains('hidden')) {
      downloadLink.classList.add('hidden');
    }
  });
}