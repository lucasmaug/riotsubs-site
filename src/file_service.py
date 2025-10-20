import os
import uuid

class FileService:
    """Serviço responsável por operações com arquivos"""
    
    def __init__(self, upload_folder):
        self.upload_folder = upload_folder
        os.makedirs(upload_folder, exist_ok=True)
    
    def save_uploaded_file(self, file, filename):
        """Salva o arquivo enviado com nome único"""
        unique_id = uuid.uuid4().hex[:8]
        safe_filename = f"{unique_id}_{filename}"
        filepath = os.path.join(self.upload_folder, safe_filename)
        
        file.save(filepath)
        return filepath, safe_filename
    
    def read_file_content(self, filepath, encoding='utf-8'):
        """Lê o conteúdo do arquivo com tratamento de encoding"""
        encodings = [encoding, 'latin-1', 'cp1252', 'iso-8859-1']
        
        for enc in encodings:
            try:
                with open(filepath, 'r', encoding=enc) as f:
                    content = f.read()
                    if content and '�' not in content:
                        return content
            except UnicodeDecodeError:
                continue
        
        raise ValueError("Não foi possível decodificar o arquivo. Use UTF-8 ou Latin-1")
    
    def save_translated_file(self, content, original_filename):
        """Salva o conteúdo traduzido em um novo arquivo"""
        translated_filename = f"traduzido_{original_filename}"
        translated_path = os.path.join(self.upload_folder, translated_filename)
        
        with open(translated_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return translated_filename
    
    def cleanup_file(self, filepath):
        """Remove arquivo temporário"""
        if filepath and os.path.exists(filepath):
            os.remove(filepath)