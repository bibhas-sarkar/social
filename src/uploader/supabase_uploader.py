import os
import time
import logging
from pathlib import Path
from typing import List, Optional
import requests

logger = logging.getLogger(__name__)


class SupabaseStorageUploader:
    """Uploads locally rendered card PNGs to Supabase Storage and returns public URLs."""

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ):
        self.supabase_url = (supabase_url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY", "")
        self.bucket_name = bucket_name or os.getenv("SUPABASE_BUCKET", "social-cards")

    @property
    def is_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_key and self.bucket_name)

    def upload_file(self, file_path: Path, remote_filename: Optional[str] = None) -> str:
        """Upload a single file to Supabase Storage and return its public URL."""
        if not self.is_configured:
            raise ValueError("Supabase Storage credentials (SUPABASE_URL, SUPABASE_KEY) are not configured.")

        filename = remote_filename or file_path.name
        upload_url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{filename}"

        headers = {
            "Authorization": f"Bearer {self.supabase_key}",
            "apikey": self.supabase_key,
            "Content-Type": "image/png",
            "x-upsert": "true",  # Overwrite if exists
        }

        with open(file_path, "rb") as f:
            file_data = f.read()

        response = requests.post(upload_url, headers=headers, data=file_data, timeout=30)
        
        if response.status_code not in (200, 201):
            # Try PUT if POST fails
            put_response = requests.put(upload_url, headers=headers, data=file_data, timeout=30)
            if put_response.status_code not in (200, 201):
                raise RuntimeError(
                    f"Failed to upload {file_path.name} to Supabase bucket '{self.bucket_name}': "
                    f"Status {response.status_code} - {response.text}"
                )

        public_url = f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{filename}"
        logger.info(f"Uploaded {file_path.name} -> {public_url}")
        return public_url

    def upload_carousel_images(self, image_paths: List[Path], prefix: str = "matchday") -> List[str]:
        """Upload all carousel PNG cards and return list of public HTTPS URLs with unique timestamps."""
        urls = []
        batch_ts = int(time.time())
        for idx, p in enumerate(image_paths, start=1):
            remote_name = f"{prefix}_{batch_ts}_slide_{idx}_{p.name}"
            public_url = self.upload_file(p, remote_filename=remote_name)
            urls.append(public_url)
        return urls
