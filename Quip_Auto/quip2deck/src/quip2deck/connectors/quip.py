# Stub: in a real build, implement Quip API calls here.
# For the starter, we assume HTML is provided directly to the API/CLI.
class QuipConnector:
    def __init__(self, token: str | None = None):
        self.token = token

    def get_document_html(self, thread_id: str) -> str:
        raise NotImplementedError("Quip API not implemented in starter.")
