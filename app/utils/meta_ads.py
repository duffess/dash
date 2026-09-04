import requests
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class MetaAdsService:
    API_VERSION = "v26.0"
    GRAPH_BASE_URL = f"https://graph.facebook.com/{API_VERSION}"
    AUTH_BASE_URL = f"https://www.facebook.com/{API_VERSION}"

    def __init__(self, app_id: str, app_secret: str, redirect_uri: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.redirect_uri = redirect_uri

    def get_auth_url(self, state: str) -> str:
        """
        Gera a URL para o usuário fazer o login e autorizar a aplicação.
        """
        scopes = "ads_read"
        url = (
            f"{self.AUTH_BASE_URL}/dialog/oauth?"
            f"client_id={self.app_id}&"
            f"redirect_uri={self.redirect_uri}&"
            f"state={state}&"
            f"scope={scopes}"
        )
        return url

    def exchange_code_for_token(self, code: str) -> str:
        """
        Troca o código e gera um Long Lived Access Token.
        """
        # 1. Troca code por short-lived token
        url = f"{self.GRAPH_BASE_URL}/oauth/access_token"
        params = {
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "client_secret": self.app_secret,
            "code": code
        }
        try:
            res = requests.get(url, params=params, timeout=30)
            res.raise_for_status()
        except requests.RequestException as exc:
            response = getattr(exc, "response", None)
            detail = "Erro de rede ao trocar o codigo OAuth"
            status_code = "sem resposta"
            if response is not None:
                status_code = response.status_code
                try:
                    detail = response.json().get("error", {}).get("message", detail)
                except ValueError:
                    detail = "A Meta recusou a troca do codigo OAuth"
            raise RuntimeError(
                f"Falha ao trocar o codigo OAuth da Meta ({status_code}): {detail}"
            ) from exc
        data = res.json()
        short_lived_token = data.get("access_token")

        if not short_lived_token:
            raise Exception("Falha ao obter short-lived token")

        # 2. Troca short-lived por long-lived token
        long_params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "fb_exchange_token": short_lived_token
        }
        try:
            long_res = requests.get(url, params=long_params, timeout=30)
            long_res.raise_for_status()
        except requests.RequestException as exc:
            response = getattr(exc, "response", None)
            detail = "Erro de rede ao gerar token de longa duracao"
            status_code = "sem resposta"
            if response is not None:
                status_code = response.status_code
                try:
                    detail = response.json().get("error", {}).get("message", detail)
                except ValueError:
                    detail = "A Meta recusou a geracao do token de longa duracao"
            raise RuntimeError(
                f"Falha ao gerar token de longa duracao da Meta ({status_code}): {detail}"
            ) from exc
        long_data = long_res.json()
        
        return long_data.get("access_token", short_lived_token)
    
    def fetch_ad_accounts(self, access_token: str) -> List[str]:
        """
        Busca as Ad Accounts associadas àquele token.
        """
        url = f"{self.GRAPH_BASE_URL}/me/adaccounts"
        params = {
            "access_token": access_token,
            "fields": "id,account_id,name"
        }
        res = requests.get(url, params=params)
        res.raise_for_status()
        data = res.json()
        # Retorna lista de account_ids
        return [acc["id"] for acc in data.get("data", [])]

    def fetch_campaigns(self, access_token: str, ad_account_id: str) -> List[Dict[str, Any]]:
        """
        Puxa todas as campanhas, formatando no padrão DashFlow.
        (Nesta V1, se apenas a conexão for feita, o Mock preenche a UI, 
        mas deixamos a engine real pronta abaixo).
        """
        # Nota: ad_account_id geralmente já vem com o prefixo 'act_', se não vier, adicionamos.
        account_path = ad_account_id if str(ad_account_id).startswith('act_') else f"act_{ad_account_id}"
        
        url = f"{self.GRAPH_BASE_URL}/{account_path}/campaigns"
        params = {
            "access_token": access_token,
            "fields": "id,name,status,objective,start_time,stop_time,daily_budget,lifetime_budget,insights{spend,impressions,clicks,cpc,cpm,ctr,actions}",
            "limit": 50
        }
        
        try:
            res = requests.get(url, params=params)
            res.raise_for_status()
            data = res.json().get("data", [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Meta Graph API Erro: {e}")
            raise Exception(f"Graph API Error: {res.text if res else str(e)}")

        formatted = []
        for camp in data:
            # Extração de Insights (Métricas de Performance)
            insights = camp.get("insights", {}).get("data", [])
            insight_data = insights[0] if insights else {}
            
            spend = float(insight_data.get("spend", 0))
            impressions = int(insight_data.get("impressions", 0))
            clicks = int(insight_data.get("clicks", 0))
            cpc_calc = float(insight_data.get("cpc", 0))
            cpm_calc = float(insight_data.get("cpm", 0))
            ctr_calc = float(insight_data.get("ctr", 0))
            
            # Conta Conversões (actions on Meta that match 'purchase' or 'lead')
            actions = insight_data.get("actions", [])
            conversions = 0
            for action in actions:
                if action.get("action_type") in ["purchase", "lead", "offsite_conversion.fb_pixel_purchase"]:
                    conversions += int(action.get("value", 0))
                    
            budget = float(camp.get("daily_budget", 0) or camp.get("lifetime_budget", 0)) / 100.0

            formatted.append({
                "external_id": f"meta_{camp.get('id')}",
                "platform_account_id": account_path,
                "name": camp.get("name", "Unknown Campaign"),
                "status": camp.get("status", "UNKNOWN").lower(),
                "objective": camp.get("objective", "UNKNOWN").lower(),
                "budget": budget,
                "daily_budget": budget,
                "spend": spend,
                "impressions": impressions,
                "clicks": clicks,
                "conversions": conversions,
                "ctr": ctr_calc,
                "cpc": cpc_calc,
                "cpm": cpm_calc,
                "start_date": camp.get("start_time", "").split("T")[0] if camp.get("start_time") else "2024-01-01",
                "end_date": camp.get("stop_time", "").split("T")[0] if camp.get("stop_time") else None
            })
            
        return formatted
