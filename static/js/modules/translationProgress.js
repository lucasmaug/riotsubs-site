export function setupTranslationProgress() {
  const stepOptions = document.getElementById("step-options");
  const stepProgress = document.getElementById("step-progress");
  const stepFinal = document.getElementById("step-final");
  const progressFill = document.getElementById("progress-fill");

  document.getElementById("translate-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    
    // Mostra tela de progresso
    stepOptions.classList.add("hidden");
    stepProgress.classList.remove("hidden");

    try {
      // 1. Pega o arquivo que já foi carregado
      const fileUpload = document.getElementById("file-upload");
      const file = fileUpload.files[0];
      
      if (!file) {
        throw new Error('Nenhum arquivo selecionado');
      }

      // 2. Faz o upload e monitora progresso REAL com chunks
      const response = await uploadFileWithProgress(file);
      console.log("Tradução completa:", response);
      
      if (response.success) {
        // Mostra o link de download
        const downloadLink = document.getElementById('download-link');
        downloadLink.href = response.download_url;
        downloadLink.classList.remove('hidden');

        // Atualiza o nome do arquivo
        document.getElementById('file-name-final').textContent = response.translated;
        
        // Mostra tela final
        stepProgress.classList.add("hidden");
        stepFinal.classList.remove("hidden");
      } else {
        throw new Error(response.error);
      }
      
    } catch (error) {
      console.error('Erro na tradução:', error);
      alert('Ocorreu um erro durante a tradução: ' + error.message);
      location.reload();
    }
  });

  document.getElementById("cancel-progress").addEventListener("click", () => {
    location.reload();
  });

  document.getElementById("restart-process").addEventListener("click", () => {
    location.reload();
  });
}

// Função para upload com progresso real
async function uploadFileWithProgress(file) {
  const formData = new FormData();
  formData.append('srt_file', file);
  formData.append('lang', document.getElementById('lang')?.value || 'pt');
  
  try {
    // 1. Inicia a tradução assíncrona com chunks
    const startResponse = await fetch('/start-translation', {
      method: 'POST',
      body: formData
    });
    
    const startData = await startResponse.json();
    
    if (!startData.success) {
      throw new Error(startData.error || 'Erro ao iniciar tradução');
    }
    
    const translationId = startData.translation_id;
    
    // 2. Monitora o progresso em tempo real
    return await monitorTranslationProgress(translationId);
    
  } catch (error) {
    console.error('Erro no upload:', error);
    throw error;
  }
}

// Função para monitorar o progresso com chunks
async function monitorTranslationProgress(translationId) {
  return new Promise((resolve, reject) => {
    const checkProgress = async () => {
      try {
        const response = await fetch(`/translation-status/${translationId}`);
        const status = await response.json();
        
        if (status.error) {
          reject(new Error(status.error));
          return;
        }
        
        // Atualiza a barra de progresso
        const progressFill = document.getElementById("progress-fill");
        if (progressFill) {
          progressFill.style.width = status.progress + "%";
          
          // Mostra informações dos chunks se disponível
          if (status.chunks_processed !== undefined && status.total_chunks !== undefined) {
            progressFill.textContent = `${status.progress}% (${status.chunks_processed}/${status.total_chunks} blocos)`;
          } else {
            progressFill.textContent = status.progress + "%";
          }
        }
        
        // Log da mensagem de status
        if (status.message) {
          console.log(`Status: ${status.message}`);
        }
        
        if (status.status === 'completed') {
          resolve({
            success: true,
            original: status.original_filename || 'arquivo.srt',
            translated: status.translated_filename,
            download_url: status.download_url
          });
        } else if (status.status === 'error') {
          reject(new Error(status.error || 'Erro na tradução'));
        } else {
          // Continua verificando a cada segundo
          setTimeout(checkProgress, 1000);
        }
      } catch (error) {
        reject(error);
      }
    };
    
    // Inicia o monitoramento
    checkProgress();
  });
}