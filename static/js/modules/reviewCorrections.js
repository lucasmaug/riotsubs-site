export function setupReviewCorrections() {
  const applyBtn = document.getElementById('apply-corrections-btn');
  const skipBtn = document.getElementById('skip-corrections-btn');

  if (applyBtn) {
    applyBtn.addEventListener('click', () => applyCorrections());
  }

  if (skipBtn) {
    skipBtn.addEventListener('click', () => skipToDownload());
  }
}

export function showReviewScreen(translationId, failedDetails, downloadUrl, translatedFilename) {
  const stepProgress = document.getElementById('step-progress');
  const stepReview = document.getElementById('step-review');

  window._reviewData = { translationId, failedDetails, downloadUrl, translatedFilename };

  const container = document.getElementById('review-blocks');
  container.innerHTML = '';

  const count = document.createElement('p');
  count.className = 'review-count';
  count.textContent = `${failedDetails.length} bloco(s) precisam de revisão`;
  container.appendChild(count);

  failedDetails.forEach((detail) => {
    const lines = detail.original_text.split('\n');
    const timestamp = lines.find(l => l.includes('-->')) || '';
    const dialogLines = lines.filter(l => {
      const trimmed = l.trim();
      return trimmed && !/^\d+$/.test(trimmed) && !trimmed.includes('-->');
    }).join('\n');

    const block = document.createElement('div');
    block.className = 'review-block';

    const header = document.createElement('div');
    header.className = 'review-block-header';
    header.textContent = timestamp;

    const originalLabel = document.createElement('div');
    originalLabel.className = 'review-block-label';
    originalLabel.textContent = 'Texto original:';

    const original = document.createElement('div');
    original.className = 'review-block-original';
    original.textContent = dialogLines;

    const translationLabel = document.createElement('div');
    translationLabel.className = 'review-block-label';
    translationLabel.textContent = 'Sua tradução:';

    const textarea = document.createElement('textarea');
    textarea.dataset.chunkIndex = detail.chunk_index;
    textarea.placeholder = 'Digite a tradução para este trecho...';
    textarea.value = detail.original_text;

    block.append(header, originalLabel, original, translationLabel, textarea);
    container.appendChild(block);
  });

  stepProgress.classList.add('hidden');
  stepReview.classList.remove('hidden');
}

async function applyCorrections() {
  const { translationId, failedDetails } = window._reviewData;

  const textareas = document.querySelectorAll('#review-blocks textarea');
  const corrections = [];

  textareas.forEach(ta => {
    const correctedText = ta.value.trim();
    const chunkIndex = parseInt(ta.dataset.chunkIndex, 10);
    const detail = failedDetails.find(d => d.chunk_index === chunkIndex);

    if (correctedText && detail) {
      corrections.push({
        chunk_index: chunkIndex,
        original_text: detail.original_text,
        corrected_text: correctedText,
      });
    }
  });

  try {
    const applyBtn = document.getElementById('apply-corrections-btn');
    applyBtn.disabled = true;
    applyBtn.textContent = 'Aplicando correções...';

    const response = await fetch(`/apply-corrections/${translationId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ corrections }),
    });

    const data = await response.json();

    if (data.success) {
      goToFinalScreen(data.download_url, data.corrected_filename);
    } else {
      alert('Erro ao aplicar correções: ' + data.error);
      applyBtn.disabled = false;
      applyBtn.textContent = 'Baixar com correções';
    }
  } catch (error) {
    alert('Erro ao aplicar correções: ' + error.message);
    const applyBtn = document.getElementById('apply-corrections-btn');
    applyBtn.disabled = false;
    applyBtn.textContent = 'Baixar com correções';
  }
}

function skipToDownload() {
  const { downloadUrl, translatedFilename } = window._reviewData;
  goToFinalScreen(downloadUrl, translatedFilename);
}

function goToFinalScreen(downloadUrl, filename) {
  const stepReview = document.getElementById('step-review');
  const stepFinal = document.getElementById('step-final');

  const downloadLink = document.getElementById('download-link');
  downloadLink.href = downloadUrl;
  downloadLink.setAttribute('download', filename);
  downloadLink.classList.remove('hidden');

  document.getElementById('file-name-final').textContent = filename;

  stepReview.classList.add('hidden');
  stepFinal.classList.remove('hidden');
}
