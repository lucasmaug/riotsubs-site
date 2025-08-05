// Configura os listeners de eventos para a interface
export function setupFileUpload() {
  // 1. Seleciona elementos do DOM
  const fileUpload = document.getElementById("file-upload");
  const fileInfo = document.getElementById("file-info");
  const fileNameDisplay = document.getElementById("file-name");
  const uploadBtn = document.getElementById("upload-btn");

  // 2. Configura o clique no botão
  uploadBtn.addEventListener("click", () => {
    fileUpload.click(); // Dispara o input file oculto
  });

  // 3. Quando o usuário seleciona um arquivo
  fileUpload.addEventListener("change", async (e) => {
    const file = fileUpload.files[0];
    if (file) {
      // Atualiza a interface
      document.getElementById("upload-box").classList.add("hidden");
      fileInfo.classList.remove("hidden");

      // Processa o nome do arquivo
      const lang = document.getElementById("lang")?.value || "";
      let fileName = file.name;
      if (lang === "pt") {
        const ext = file.name.split('.').pop();
        const baseName = file.name.replace(/\.[^/.]+$/, "");
        fileName = `${baseName}-pt-br.${ext}`;
      }
      fileNameDisplay.textContent = fileName;
      document.getElementById("file-name-final").textContent = fileName;
      
      // 4. ENVIA O ARQUIVO PARA O BACKEND (nova parte)
      uploadFile(file).then(response => {
        console.log("Upload completo:", response);
        // Aqui você pode adicionar mais lógica após o upload
      });

      await uploadFile(file);
    }
  });

  // 5. Configura o botão "Substituir arquivo"
  document.getElementById("replace-file").addEventListener("click", () => {
    fileUpload.value = "";
    fileInfo.classList.add("hidden");
    fileNameDisplay.textContent = "";
    document.getElementById("upload-box").classList.remove("hidden");
  });
}

// 6. Função que faz o upload REAL para o servidor
export async function uploadFile(file) {
  const formData = new FormData();
  formData.append('srt_file', file); // Corresponde ao name do input
  
  try {
    const response = await fetch('/upload', {
      method: 'POST',
      body: formData
      // O cabeçalho Content-Type é definido automaticamente como multipart/form-data
    });
    return await response.json(); // Converte a resposta para JSON
  } catch (error) {
    console.error('Erro no upload:', error);
    throw error; // Permite que outros tratem o erro
  }
}