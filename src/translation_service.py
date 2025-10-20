import requests
import time
from src.config import Config

class TranslationService:
    """Serviço responsável pela tradução usando DeepSeek API"""
    
    def __init__(self):
        self.use_mock = Config.USE_MOCK_API
        self.api_url = Config.DEEPSEEK_API_URL
        self.api_key = Config.DEEPSEEK_API_KEY
    
    def translate(self, text):
        """Executa a tradução do texto"""
        if self.use_mock:
            return self._mock_translate(text)
        else:
            return self._real_translate(text)
    
    def _real_translate(self, text):
        """Chama a API real do DeepSeek"""
        if not self.api_key:
            raise ValueError("Chave API não configurada")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        system_prompt = """Você é um tradutor profissional de legendas SRT. 
        Sua tarefa é traduzir APENAS o texto dos diálogos, mantendo:
        - Números de sequência intactos
        - Timestamps no formato exato HH:MM:SS,ms --> HH:MM:SS,ms
        - Formatação original
        Não adicione comentários ou explicações."""
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Traduza este SRT para português:\n\n{text}"}
            ],
            "temperature": 0.1
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            return response.json()["choices"][0]["message"]["content"]
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Erro na API DeepSeek: {str(e)}"
            if e.response:
                error_msg += f" - Resposta: {e.response.text}"
            raise Exception(error_msg)
    
    def _mock_translate(self, text):
        """Mock da API para desenvolvimento"""
        print("🔧 Usando MOCK da API DeepSeek - nenhum crédito será gasto")
        
        time.sleep(1)
        
        lines = text.split('\n')
        translated_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line.isdigit():
                translated_lines.append(line)
                i += 1
                continue
                
            if i < len(lines) and '-->' in lines[i]:
                translated_lines.append(lines[i])
                i += 1
                continue
                
            if line and (i == 0 or not lines[i-1].strip() or '-->' in lines[i-1]):
                translated_line = f"[TRADUZIDO] {line}"
                translated_lines.append(translated_line)
            else:
                translated_lines.append(lines[i])
                
            i += 1
        
        return '\n'.join(translated_lines)