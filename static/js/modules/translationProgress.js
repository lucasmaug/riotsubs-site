import { showReviewScreen } from './reviewCorrections.js';

export function setupTranslationProgress() {
  const stepOptions  = document.getElementById('step-options');
  const stepProgress = document.getElementById('step-progress');
  const stepFinal    = document.getElementById('step-final');

  let currentTranslationId = null;

  document.getElementById('translate-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const fileUpload  = document.getElementById('file-upload');
    const lang        = document.getElementById('lang')?.value || '';
    const mediaType   = document.getElementById('media-type')?.value || '';
    const instructions = document.getElementById('instructions')?.value?.trim() || '';

    const file = fileUpload?.files[0];
    if (!file) { alert('Nenhum arquivo selecionado.'); return; }
    if (!lang)  { alert('Selecione o idioma de destino.'); return; }

    stepOptions.classList.add('hidden');
    stepProgress.classList.remove('hidden');

    try {
      const response = await uploadFileWithProgress(
        file, lang, mediaType, instructions, (id) => { currentTranslationId = id; }
      );

      if (response.success && !response.skipFinalScreen) {
        const outputName = response.translated_filename || file.name;

        const downloadLink = document.getElementById('download-link');
        downloadLink.href = response.download_url;
        downloadLink.setAttribute('download', outputName);
        downloadLink.classList.remove('hidden');

        document.getElementById('file-name-final').textContent = outputName;

        stepProgress.classList.add('hidden');
        stepFinal.classList.remove('hidden');
      } else if (!response.success) {
        throw new Error(response.error || 'Erro desconhecido.');
      }

    } catch (error) {
      console.error('Erro na tradução:', error);
      alert('Ocorreu um erro durante a tradução: ' + error.message);
      location.reload();
    }
  });

  document.getElementById('cancel-progress').addEventListener('click', async () => {
    if (currentTranslationId) {
      await fetch(`/cancel-translation/${currentTranslationId}`, { method: 'POST' });
    }
    location.reload();
  });
  document.getElementById('restart-process').addEventListener('click', () => location.reload());
}

async function uploadFileWithProgress(file, lang, mediaType, instructions, onStarted) {
  const formData = new FormData();
  formData.append('srt_file', file);
  formData.append('lang', lang);
  formData.append('media_type', mediaType);
  formData.append('instructions', instructions);

  const startResponse = await fetch('/start-translation', {
    method: 'POST',
    body: formData,
  });

  const startData = await startResponse.json();
  if (!startData.success) throw new Error(startData.error || 'Erro ao iniciar tradução.');

  if (onStarted) onStarted(startData.translation_id);

  return monitorTranslationProgress(startData.translation_id);
}

function monitorTranslationProgress(translationId) {
  return new Promise((resolve, reject) => {
    const check = async () => {
      try {
        const res    = await fetch(`/translation-status/${translationId}`);
        const status = await res.json();

        if (status.error) { reject(new Error(status.error)); return; }

        const fill = document.getElementById('progress-fill');
        if (fill) {
          const pct = status.progress ?? 0;
          fill.style.width = pct + '%';
          fill.textContent  = pct + '%';
        }

        const msg = document.getElementById('progress-message');
        if (msg && status.message) msg.textContent = status.message;

        if (status.status === 'completed') {
          const hasFailed = status.failed_details && status.failed_details.length > 0;

          if (hasFailed) {
            showReviewScreen(
              translationId,
              status.failed_details,
              status.download_url,
              status.translated_filename
            );
            resolve({ success: true, skipFinalScreen: true });
          } else {
            resolve({
              success:             true,
              download_url:        status.download_url,
              translated_filename: status.translated_filename,
            });
          }
        } else if (status.status === 'error') {
          reject(new Error(status.error || 'Erro na tradução.'));
        } else if (status.status === 'cancelled') {
          reject(new Error('Tradução cancelada.'));
        } else {
          setTimeout(check, 1000);
        }
      } catch (err) {
        reject(err);
      }
    };

    check();
  });
}
