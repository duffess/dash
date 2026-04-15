import json
import logging
from typing import List, Dict, Any
import openai
from app.config import get_settings

logger = logging.getLogger(__name__)

def generate_insights_for_campaigns(campaigns_data: List[Dict[str, Any]]) -> str:
    settings = get_settings()
    
    if not settings.openai_api_key:
        return "⚠️ A chave da OpenAI não foi configurada. Configure `OPENAI_API_KEY` nas variáveis de ambiente para habilitar o Cérebro de IA do DashFlow."
        
    client = openai.OpenAI(api_key=settings.openai_api_key)
    
    # Prepara o payload de dados focado no essencial
    simplified_data = []
    for c in campaigns_data:
        simplified_data.append({
            "name": c.get("name"),
            "status": c.get("status"),
            "spend": c.get("spend"),
            "clicks": c.get("clicks"),
            "conversions": c.get("conversions"),
            "ctr": c.get("ctr"),
            "cpc": c.get("cpc")
        })
        
    system_prompt = """Você é um Analista de Tráfego Pago B2B Sênior. 
Aja de forma letal, direta e pragmática. 
Analise as campanhas fornecidas e gere um relatório executivo em Markdown com:
1. **Diagnóstico Geral:**
2. **Ação Imediata:** (o que pausar ou escalar agora)
3. **Oportunidade:** (onde focar para crescer)

Use marcadores e negrito. Seja breve. Formate o texto de forma limpa, pule UMA LINHA INTEIRA entre os parágrafos para oxigenar o texto. Use os dados numéricos apresentados na análise e escreva em Português do Brasil."""

    user_message = f"Aqui estão os dados das campanhas:\n{json.dumps(simplified_data, indent=2)}\n\nGere o insight crítico."

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=600,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Erro ao chamar OpenAI: {e}")
        return f"❌ Erro ao processar inteligência artificial: {str(e)}"
