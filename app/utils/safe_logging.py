"""Keep OAuth codes and signed state out of Uvicorn's access log."""
import logging


class OAuthAccessLogFilter(logging.Filter):
    def filter(self, record):
        # Uvicorn access records: client, method, request target, HTTP version, status.
        if isinstance(record.args, tuple) and len(record.args) == 5:
            target = record.args[2]
            if isinstance(target, str):
                path = target.split("?", 1)[0]
                if path.rstrip("/") in {"/auth/google/callback", "/auth/meta/callback"}:
                    record.args = (*record.args[:2], path, *record.args[3:])
        return True


def configure_access_logging():
    logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(item, OAuthAccessLogFilter) for item in logger.filters):
        logger.addFilter(OAuthAccessLogFilter())
