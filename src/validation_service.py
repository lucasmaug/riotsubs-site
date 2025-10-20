import os
from werkzeug.utils import secure_filename

class ValidationService:
    """Serviço responsável por validações de arquivo e conteúdo"""
    
    def __init__(self, allowed_extensions, max_file_size):
        self.allowed_extensions = allowed_extensions
        self.max_file_size = max_file_size
    
    def is_file_allowed(self, filename):
        """Verifica se a extensão do arquivo é permitida"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def validate_file_upload(self, uploaded_file):
        """Valida o arquivo enviado pelo usuário"""
        if not uploaded_file:
            raise ValueError("Nenhum arquivo enviado")
        
        if uploaded_file.filename == '':
            raise ValueError("Nome de arquivo vazio")
        
        if not self.is_file_allowed(uploaded_file.filename):
            raise ValueError(f"Apenas arquivos {', '.join(self.allowed_extensions)} são permitidos")
        
        return secure_filename(uploaded_file.filename)
    
    def validate_srt_content(self, content):
        """Valida se o conteúdo parece ser um arquivo SRT válido"""
        lines = content.split('\n')
        if len(lines) < 3:
            raise ValueError("Arquivo SRT muito curto ou inválido")
        
        # Verifica padrão básico de SRT
        has_srt_pattern = any(
            line.strip().isdigit() and i + 1 < len(lines) and '-->' in lines[i + 1]
            for i, line in enumerate(lines[:10])
        )
        
        if not has_srt_pattern:
            raise ValueError("Arquivo não segue o formato SRT padrão")
        
        return True