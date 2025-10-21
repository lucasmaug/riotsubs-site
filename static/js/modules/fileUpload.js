// Configura os listeners de eventos para a interface
export function setupFileUpload() {
  // 1. Seleciona elementos do DOM
  const fileUpload = document.getElementById("file-upload");
  const fileInfo = document.getElementById("file-info");
  const fileNameDisplay = document.getElementById("file-name");
  const uploadBtn = document.getElementById("upload-btn");

  // 2. Configura o clique no botão
  uploadBtn.addEventListener("click", () => {
    fileUpload.click();
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
    }
  });

  // 4. Configura o botão "Substituir arquivo"
  document.getElementById("replace-file").addEventListener("click", () => {
    fileUpload.value = "";
    fileInfo.classList.add("hidden");
    fileNameDisplay.textContent = "";
    document.getElementById("upload-box").classList.remove("hidden");
    
    // Esconde o link de download se estiver visível
    const downloadLink = document.getElementById('download-link');
    if (!downloadLink.classList.contains('hidden')) {
      downloadLink.classList.add('hidden');
    }
  });
}