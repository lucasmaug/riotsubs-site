export function setupDragDrop() {
  const uploadBox = document.getElementById("upload-box");
  const uploadButton = document.getElementById("upload-btn");
  const dropMessage = document.getElementById("drop-message");
  const fileUpload = document.getElementById("file-upload");
  const fileInfo = document.getElementById("file-info");
  const fileNameDisplay = document.getElementById("file-name");

  // Eventos de drag
  ['dragenter', 'dragover'].forEach(eventName => {
    uploadBox.addEventListener(eventName, e => {
      e.preventDefault();
      e.stopPropagation();
      uploadBox.classList.add("dragover");
      dropMessage.textContent = "Solte aqui para começar a tradução";
      uploadButton.style.display = "none";
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    uploadBox.addEventListener(eventName, e => {
      e.preventDefault();
      e.stopPropagation();
      uploadBox.classList.remove("dragover");
      dropMessage.textContent = "Clique ou arraste o arquivo .SRT aqui";
      uploadButton.style.display = "inline-block";
    });
  });

  uploadBox.addEventListener("drop", async e => {  // Adicionei async aqui
    const dt = e.dataTransfer;
    const files = dt.files;

    if (files.length) {
      const file = files[0];
      
      // Atualiza a interface
      fileInfo.classList.remove("hidden");
      uploadBox.classList.add("hidden");

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

      // Cria um novo FileList sintético para o input
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);
      fileUpload.files = dataTransfer.files;

      // Dispara o evento change manualmente
      const event = new Event('change');
      fileUpload.dispatchEvent(event);
      
      // Opcional: Chama diretamente o upload
      // await uploadFile(file); // Descomente se estiver importando uploadFile
    }
  });
}