import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configurações da aplicação"""
    USE_MOCK_API = False  # Alterar para False quando quiser usar a API real
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions" if not USE_MOCK_API else None
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY") if not USE_MOCK_API else None
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    ALLOWED_EXTENSIONS = {'srt'}
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
    
    @classmethod
    def validate_config(cls):
        """Valida se as configurações necessárias estão presentes"""
        if not cls.USE_MOCK_API and not cls.DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY não configurada no arquivo .env")
        
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)