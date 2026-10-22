from sqlalchemy import and_, or_
from app.models.campaign import Campaign
from app.models.integration import ClientIntegration


def real_campaign_filter():
    """Exclude only the exact IDs emitted by the retired demo generator.

    Keep legacy demo rows in storage; never present them as API data.
    """
    prefix = Campaign.platform + "_" + Campaign.client_id + "_"
    return and_(
        Campaign.external_id.notin_([prefix + str(i) for i in range(3)]),
        or_(
            Campaign.integration_id.is_(None),
            Campaign.integration.has(or_(
                ClientIntegration.last_sync_at.is_(None),
                Campaign.last_synced_at == ClientIntegration.last_sync_at,
            )),
        ),
    )
