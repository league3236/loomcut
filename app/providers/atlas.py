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


def _unwrap(body: dict) -> dict:
    # Atlas 응답은 {"data": {...}} 형태
    return body.get("data") if isinstance(body.get("data"), dict) else body


class AtlasCloudProvider:
    """Atlas Cloud API (Seedance 2.0 등). 제출 후 prediction id로 폴링하는 비동기 방식."""

    name = "atlas"

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _auth(self) -> dict:
        if not self.api_key:
            raise ProviderError("ATLAS_API_KEY is not set")
        return {"Authorization": f"Bearer {self.api_key}"}

    @staticmethod
    def _to_result(body: dict) -> GenerationResult:
        data = _unwrap(body)
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
        self,
        *,
        model: str,
        prompt: str,
        duration: int,
        image: str | None = None,
        last_image: str | None = None,
        reference_images: list[str] | None = None,
    ) -> GenerationResult:
        payload: dict = {"model": model, "prompt": prompt, "duration": duration}
        if image:
            payload["image"] = image
        if last_image:
            payload["last_image"] = last_image
        if reference_images:
            payload["reference_images"] = reference_images

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self.base_url}/api/v1/model/generateVideo",
                json=payload,
                headers=self._auth(),
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
                headers=self._auth(),
            )
        if r.status_code >= 400:
            raise ProviderError(f"Atlas Cloud error {r.status_code}: {r.text[:500]}")
        return self._to_result(r.json())

    async def upload_media(self, file_name: str, content: bytes, content_type: str) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{self.base_url}/api/v1/model/uploadMedia",
                headers=self._auth(),
                files={"file": (file_name, content, content_type)},
            )
        if r.status_code >= 400:
            raise ProviderError(f"Atlas Cloud upload error {r.status_code}: {r.text[:500]}")
        url = _unwrap(r.json()).get("download_url")
        if not url:
            raise ProviderError("Atlas Cloud upload response has no download_url")
        return url
