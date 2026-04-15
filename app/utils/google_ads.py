import logging
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

logger = logging.getLogger(__name__)

class GoogleAdsService:
    def __init__(self, developer_token: str, client_id: str, client_secret: str):
        self.developer_token = developer_token
        self.client_id = client_id
        self.client_secret = client_secret

    def _get_client(self, refresh_token: str, customer_id: Optional[str] = None) -> GoogleAdsClient:
        """Instancia o cliente oficial do Google Ads."""
        config = {
            "developer_token": self.developer_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "use_proto_plus": True
        }
        if customer_id:
            # Se for MCC, o login-customer-id deve ser o ID da MCC
            # Mas para simplificar no MVP, usamos o próprio customer_id se ele for o alvo
            config["login_customer_id"] = customer_id.replace("-", "")
            
        return GoogleAdsClient.load_from_dict(config)

    def fetch_campaigns(self, customer_id: str, refresh_token: str, days: int = 30) -> List[Dict[str, Any]]:
        """Busca campanhas e métricas usando o SDK oficial."""
        if not customer_id:
            logger.error("customer_id não fornecido")
            return []

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
                campaign.start_date,
                campaign.end_date
            FROM campaign
            WHERE campaign.status != 'REMOVED'
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
                status = status_map.get(status_raw, status_raw)

                results.append({
                    "external_id": str(campaign.id),
                    "name": campaign.name,
                    "status": status,
                    "objective": str(campaign.advertising_channel_type.name).lower(),
                    "spend": round(spend, 2),
                    "impressions": int(metrics.impressions),
                    "clicks": int(metrics.clicks),
                    "conversions": float(metrics.conversions),
                    "start_date": campaign.start_date,
                    "end_date": campaign.end_date,
                    "platform_account_id": customer_id
                })

            return results
        except GoogleAdsException as ex:
            logger.error(f"Erro no SDK Google Ads: {ex.error.code_pb} - {ex.message}")
            for error in ex.failure.errors:
                logger.error(f"\tError with message: {error.message}")
            return []
        except Exception as e:
            logger.error(f"Erro genérico no fetch_campaigns: {str(e)}")
            return []

    def list_accessible_customers(self, refresh_token: str) -> List[str]:
        """Lista IDs de clientes acessíveis para o token."""
        client = self._get_client(refresh_token)
        customer_service = client.get_service("CustomerService")
        
        try:
            customer_resource_names = customer_service.list_accessible_customers()
            return [name.split("/")[-1] for name in customer_resource_names.resource_names]
        except Exception as e:
            logger.error(f"Erro ao listar clientes acessíveis: {str(e)}")
            return []
