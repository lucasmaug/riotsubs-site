import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # USE_MOCK_API lido do .env — True em desenvolvimento, False em produção
    # No .env local coloque: USE_MOCK_API=true
    # No Railway/Heroku deixe sem essa variável (padrão False)
    USE_MOCK_API = os.getenv('USE_MOCK_API', 'false').lower() == 'true'

    DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    ALLOWED_EXTENSIONS = {'srt'}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB (aumentado de 2MB — arquivos longos passavam do limite)

    @classmethod
    def validate_config(cls):
        if not cls.USE_MOCK_API and not cls.DEEPSEEK_API_KEY:
            raise ValueError(
                'DEEPSEEK_API_KEY não configurada. '
                'Crie um arquivo .env com DEEPSEEK_API_KEY=sua_chave '
                'ou adicione a variável de ambiente no painel do Railway/Heroku.'
            )
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
