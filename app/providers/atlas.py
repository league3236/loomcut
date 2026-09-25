import httpx

from app.providers.base import GenerationResult, ProviderError

STATUS_MAP = {
    "created": "pending",
    "queued": "pending",
    "pending": "pending",
    "starting": "pending",
    "processing": "processing",
    "running": "processing",
    "in_progress": "processing",
    "completed": "completed",
    "succeeded": "completed",
    "success": "completed",
    "failed": "failed",
    "error": "failed",
    "canceled": "failed",
    "cancelled": "failed",
}


class AtlasCloudProvider:
    """Atlas Cloud API (Seedance 2.0 등). 제출 후 prediction id로 폴링하는 비동기 방식."""

    name = "atlas"

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict:
        if not self.api_key:
            raise ProviderError("ATLAS_API_KEY is not set")
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    @staticmethod
    def _to_result(body: dict) -> GenerationResult:
        data = body.get("data") if isinstance(body.get("data"), dict) else body
        raw_status = str(data.get("status", "pending")).lower()
        status = STATUS_MAP.get(raw_status, "processing")
        outputs = data.get("outputs") or []
        error = data.get("error")
        return GenerationResult(
            external_id=data.get("id"),
            status=status,
            video_url=outputs[0] if status == "completed" and outputs else None,
            error=str(error) if status == "failed" and error else None,
        )

    async def submit(
        self, *, model: str, prompt: str, image_url: str | None, duration: int | None
    ) -> GenerationResult:
        payload: dict = {"model": model, "prompt": prompt}
        if image_url:
            payload["image"] = image_url
        if duration:
            payload["duration"] = duration

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self.base_url}/api/v1/model/generateVideo",
                json=payload,
                headers=self._headers(),
            )
        if r.status_code >= 400:
            raise ProviderError(f"Atlas Cloud error {r.status_code}: {r.text[:500]}")

        result = self._to_result(r.json())
        if not result.external_id:
            raise ProviderError("Atlas Cloud response has no prediction id")
        return result

    async def fetch(self, external_id: str) -> GenerationResult:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"{self.base_url}/api/v1/model/prediction/{external_id}",
                headers=self._headers(),
            )
        if r.status_code >= 400:
            raise ProviderError(f"Atlas Cloud error {r.status_code}: {r.text[:500]}")
        return self._to_result(r.json())
