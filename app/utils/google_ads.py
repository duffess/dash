import logging
from typing import List, Dict, Any, Optional
from google.ads.googleads.client import GoogleAdsClient

logger = logging.getLogger(__name__)

class GoogleAdsService:
    API_VERSION = "v26"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    def _get_client(self, refresh_token: str, customer_id: Optional[str] = None) -> GoogleAdsClient:
        """Instancia o cliente oficial do Google Ads."""
        config = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "use_proto_plus": True
        }
        if customer_id:
            # Se for MCC, o login-customer-id deve ser o ID da MCC
            # Mas para simplificar no MVP, usamos o próprio customer_id se ele for o alvo
            config["login_customer_id"] = customer_id.replace("-", "")
            
        return GoogleAdsClient.load_from_dict(config, version=self.API_VERSION)

    def fetch_campaigns(self, customer_id: str, refresh_token: str, days: int = 30) -> List[Dict[str, Any]]:
        """Busca campanhas e métricas usando o SDK oficial."""
        if not customer_id:
            logger.error("customer_id não fornecido")
            raise ValueError("Selecione uma conta Google Ads.")

        customer_id = customer_id.replace("-", "")
        client = self._get_client(refresh_token, customer_id)
        ga_service = client.get_service("GoogleAdsService")

        # Query GAQL - Buscamos todas as campanhas não removidas
        query = """
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                metrics.cost_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions,
                campaign_budget.amount_micros,
                campaign.start_date,
                campaign.end_date
            FROM campaign
            WHERE campaign.status != 'REMOVED'
                AND segments.date DURING LAST_30_DAYS
        """

        try:
            # Usando ga_service.search em vez de search_stream para compatibilidade com tokens de teste
            response = ga_service.search(customer_id=customer_id, query=query)
            results = []

            for row in response:
                campaign = row.campaign
                metrics = row.metrics
                
                spend = float(metrics.cost_micros) / 1_000_000
                
                # Mapping status
                status_raw = str(campaign.status.name).lower()
                status_map = {
                    "enabled": "active",
                    "paused": "paused",
                    "removed": "archived"
                }
                status = status_map.get(status_raw, "unknown")

                results.append({
                    "external_id": str(campaign.id),
                    "name": campaign.name,
                    "status": status,
                    "objective": str(campaign.advertising_channel_type.name).lower(),
                    "spend": round(spend, 2),
                    "report_metrics": {"spend": round(spend, 2), "impressions": int(metrics.impressions),
                                       "clicks": int(metrics.clicks), "conversions": float(metrics.conversions)},
                    "budget": 0,
                    "daily_budget": float(row.campaign_budget.amount_micros) / 1_000_000,
                    "ctr": round(metrics.clicks / metrics.impressions * 100, 2) if metrics.impressions else 0,
                    "cpc": round(spend / metrics.clicks, 2) if metrics.clicks else 0,
                    "cpm": round(spend / metrics.impressions * 1000, 2) if metrics.impressions else 0,
                    "impressions": int(metrics.impressions),
                    "clicks": int(metrics.clicks),
                    "conversions": float(metrics.conversions),
                    "start_date": campaign.start_date,
                    "end_date": campaign.end_date,
                    "platform_account_id": customer_id
                })

            return results
        except Exception as exc:
            raise RuntimeError("Não foi possível consultar campanhas do Google Ads. Verifique credenciais e acesso à conta.") from exc

    def list_accessible_customers(self, refresh_token: str) -> List[str]:
        """Lista IDs de clientes acessíveis para o token."""
        client = self._get_client(refresh_token)
        customer_service = client.get_service("CustomerService")
        
        try:
            customer_resource_names = customer_service.list_accessible_customers()
            return [name.split("/")[-1] for name in customer_resource_names.resource_names]
        except Exception as exc:
            raise RuntimeError("Não foi possível listar as contas Google Ads.") from exc
