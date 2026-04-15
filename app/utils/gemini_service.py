import google.generativeai as genai
import json
import logging
from typing import List, Dict, Any
from app.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        self.model = None
        self._initialized = False

    def _initialize(self):
        # Recarregar as configurações para garantir que pegamos a chave atualizada do .env
        from app.config import get_settings
        get_settings.cache_clear()
        settings = get_settings()
        
        if settings.gemini_api_key and not self._initialized:
            try:
                genai.configure(api_key=settings.gemini_api_key)
                self.model = genai.GenerativeModel('models/gemini-1.5-flash')
                self._initialized = True
                logger.info("Gemini Model inicializado com sucesso.")
            except Exception as e:
                logger.error(f"Erro ao configurar Gemini: {str(e)}")

    def generate_marketing_insights(self, campaigns_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analisa dados de campanhas e gera insights estratégicos usando Gemini.
        """
        self._initialize()
        
        if not self.model:
            return [{
                "title": "IA não configurada",
                "message": "Configure sua chave do Gemini no .env para receber insights estratégicos reais.",
                "priority": "medium"
            }]

        if not campaigns_data:
            return [{
                "title": "Sem dados para análise",
                "message": "Ainda não temos dados de campanhas suficientes para gerar insights. Tente sincronizar seu Google Ads.",
                "priority": "low"
            }]

        # Formatar dados para o prompt
        data_summary = ""
        for c in campaigns_data:
            data_summary += (
                f"- Campanha: {c.get('name')}\n"
                f"  Cliques: {c.get('clicks')}, Impressões: {c.get('impressions')}, "
                f"Custo: {c.get('spend')}, Conversões: {c.get('conversions')}\n"
            )

        prompt = f"""
        Você é um Diretor de Marketing (CMO) senior e especialista em tráfego pago.
        Analise os seguintes dados de campanhas de tráfego (Google Ads) e forneça 2 a 3 insights estratégicos curtos e acionáveis.

        DADOS DAS CAMPANHAS:
        {data_summary}

        REGRAS:
        1. Identifique anomalias positivas ou negativas (ex: CPC muito alto, CTR excelente).
        2. Dê recomendações práticas (ex: 'Aumente o orçamento da campanha X', 'Revise os criativos da campanha Y').
        3. Mantenha o tom profissional, direto e encorajador.
        4. RESPONDA EXCLUSIVAMENTE EM FORMATO JSON, seguindo esta estrutura:
        [
          {{
            "title": "Título curto do insight",
            "message": "Descrição detalhada e acionável",
            "priority": "high" | "medium" | "low"
          }}
        ]

        O JSON deve ser uma lista de objetos. Não adicione textos antes ou depois do JSON.
        """

        try:
            response = self.model.generate_content(prompt)
            raw_content = response.text.strip()
            logger.info(f"Resposta bruta do Gemini: {raw_content}")

            # Tentar encontrar um JSON array na resposta usando regex
            import re
            json_match = re.search(r'\[\s*\{.*\}\s*\]', raw_content, re.DOTALL)
            
            if json_match:
                content = json_match.group(0)
            else:
                # Fallback para limpeza manual básica
                content = raw_content.replace("```json", "").replace("```", "").strip()
            
            insights = json.loads(content)
            return insights
        except Exception as e:
            logger.error(f"Erro detalhado Gemini: {str(e)}")
            # Se for um erro de segurança/bloqueio do Google
            if "finish_reason" in str(e) or "safety" in str(e).lower():
                return [{
                    "title": "Conteúdo Bloqueado",
                    "message": "O Gemini bloqueou a resposta por motivos de segurança. Tente ajustar os nomes das campanhas.",
                    "priority": "low"
                }]
            
            return [{
                "title": "Erro na análise",
                "message": f"Erro técnico: {type(e).__name__}. Verifique se sua chave tem créditos ou se a cota foi excedida.",
                "priority": "medium"
            }]

# Instância singleton
gemini_service = GeminiService()
