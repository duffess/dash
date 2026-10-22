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
            status_code = "sem resposta"
            if response is not None:
                status_code = response.status_code
            raise RuntimeError(
                f"Falha ao trocar o codigo OAuth da Meta ({status_code}). Revise a configuração e tente conectar novamente."
            ) from None
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
            status_code = "sem resposta"
            if response is not None:
                status_code = response.status_code
            raise RuntimeError(
                f"Falha ao gerar token de longa duracao da Meta ({status_code}). Tente conectar novamente."
            ) from None
        long_data = long_res.json()
        
        return long_data.get("access_token", short_lived_token)
    
    def _get_collection(self, path: str, access_token: str, params: dict) -> List[dict]:
        """Read every page using cursors; never log credential-bearing URLs."""
        url = f"{self.GRAPH_BASE_URL}/{path}"
        params = dict(params, limit=100)
        rows = []
        seen = set()
        while True:
            try:
                response = requests.get(
                    url, params=params,
                    headers={"Authorization": f"Bearer {access_token}"}, timeout=30,
                )
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError) as exc:
                raise RuntimeError(
                    "Não foi possível consultar a Meta. Verifique o token, as permissões ads_read e o acesso à conta."
                ) from exc
            if "error" in payload or not isinstance(payload.get("data"), list):
                raise RuntimeError("A Meta retornou uma resposta inválida.")
            rows.extend(payload["data"])
            paging = payload.get("paging", {})
            if not paging.get("next"):
                return rows
            after = paging.get("cursors", {}).get("after")
            if not after or after in seen:
                raise RuntimeError("Não foi possível concluir a paginação da Meta.")
            seen.add(after)
            params["after"] = after

    def fetch_ad_accounts(self, access_token: str) -> List[str]:
        return [row["id"] for row in self._get_collection(
            "me/adaccounts", access_token, {"fields": "id,account_id,name"}
        )]

    def fetch_campaigns(self, access_token: str, ad_account_id: str) -> List[Dict[str, Any]]:
        from datetime import date

        account_path = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
        campaigns = self._get_collection(
            f"{account_path}/campaigns", access_token,
            {"fields": "id,name,status,objective,start_time,stop_time,daily_budget,lifetime_budget"},
        )
        insights = self._get_collection(
            f"{account_path}/insights", access_token,
            {"fields": "campaign_id,spend,impressions,clicks,actions",
             "level": "campaign", "date_preset": "last_30d"},
        )
        by_id = {row["campaign_id"]: row for row in insights}
        formatted = []
        for camp in campaigns:
            metrics = by_id.get(camp["id"], {})
            spend = float(metrics.get("spend", 0))
            impressions = int(metrics.get("impressions", 0))
            clicks = int(metrics.get("clicks", 0))
            actions = {a["action_type"]: float(a.get("value", 0)) for a in metrics.get("actions", [])}
            # Aggregate purchases include pixel purchases; do not count both.
            purchases = actions.get("purchase", actions.get("offsite_conversion.fb_pixel_purchase", 0))
            conversions = purchases + actions.get("lead", 0)
            # Missing actions are not evidence of zero results.
            report_metrics = {k: float(metrics[k]) for k in ("spend", "impressions", "clicks")
                              if metrics.get(k) is not None}
            if "lead" in actions:
                report_metrics["leads"] = actions["lead"]
            if "purchase" in actions or "offsite_conversion.fb_pixel_purchase" in actions:
                report_metrics["purchases"] = purchases
            status = camp.get("status", "").lower()
            if status not in {"active", "paused", "archived", "deleted"}:
                status = "unknown"
            formatted.append({
                "external_id": f"meta_{camp['id']}",
                "platform_account_id": account_path,
                "name": camp.get("name", camp["id"]),
                "status": status,
                "objective": camp.get("objective", "").lower(),
                "budget": float(camp.get("lifetime_budget", 0)) / 100,
                "daily_budget": float(camp.get("daily_budget", 0)) / 100,
                "spend": spend,
                "report_metrics": report_metrics,
                "impressions": impressions,
                "clicks": clicks,
                "conversions": conversions,
                "ctr": round(clicks / impressions * 100, 2) if impressions else 0,
                "cpc": round(spend / clicks, 2) if clicks else 0,
                "cpm": round(spend / impressions * 1000, 2) if impressions else 0,
                "start_date": date.fromisoformat(camp["start_time"][:10]) if camp.get("start_time") else None,
                "end_date": date.fromisoformat(camp["stop_time"][:10]) if camp.get("stop_time") else None,
            })
        return formatted
