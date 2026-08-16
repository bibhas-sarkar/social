import os
import time
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import requests

from config import ChannelConfig, CarouselContent

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v19.0"
GRAPH_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class PublishResult(BaseModel):
    """Publish result record for multi-platform distribution."""
    channel_key: str
    is_dry_run: bool
    instagram_post_id: Optional[str] = None
    facebook_post_id: Optional[str] = None
    published_images: List[str] = Field(default_factory=list)
    status: str = "SUCCESS"
    details: Dict[str, Any] = Field(default_factory=dict)


class MetaSocialPublisherAgent:
    """Agent responsible for Meta Graph API Instagram Carousel and Facebook Page publishing."""

    def publish_carousel(
        self,
        channel: ChannelConfig,
        carousel: CarouselContent,
        image_paths: List[Path],
        dry_run: bool = False,
        public_image_urls: Optional[List[str]] = None,
    ) -> PublishResult:
        """Publish carousel to Instagram and Facebook, or simulate in dry-run mode."""
        logger.info(
            f"[{channel.name}] Publishing carousel ({len(image_paths)} slides). Dry run: {dry_run}"
        )

        if dry_run or not channel.access_token:
            return self._simulate_publish(channel, carousel, image_paths, dry_run)

        # Real Meta Graph API publishing execution
        ig_post_id = None
        fb_post_id = None
        details = {}

        # 1. Instagram Carousel Publishing
        if channel.ig_account_id and public_image_urls:
            try:
                ig_post_id = self._publish_instagram_carousel(
                    channel.ig_account_id,
                    channel.access_token,
                    public_image_urls,
                    carousel.caption,
                )
                details["instagram"] = {"status": "published", "media_id": ig_post_id}
            except Exception as e:
                logger.error(f"Instagram publishing failed: {e}")
                details["instagram"] = {"status": "failed", "error": str(e)}

        # 2. Facebook Page Multi-Photo Posting
        if channel.fb_page_id:
            try:
                fb_post_id = self._publish_facebook_photos(
                    channel.fb_page_id,
                    channel.access_token,
                    image_paths,
                    carousel.caption,
                )
                details["facebook"] = {"status": "published", "post_id": fb_post_id}
            except Exception as e:
                logger.error(f"Facebook publishing failed: {e}")
                details["facebook"] = {"status": "failed", "error": str(e)}

        return PublishResult(
            channel_key=channel.key,
            is_dry_run=False,
            instagram_post_id=ig_post_id,
            facebook_post_id=fb_post_id,
            published_images=[str(p) for p in image_paths],
            status="SUCCESS" if (ig_post_id or fb_post_id) else "FAILED",
            details=details,
        )

    def _simulate_publish(
        self,
        channel: ChannelConfig,
        carousel: CarouselContent,
        image_paths: List[Path],
        dry_run: bool,
    ) -> PublishResult:
        """Simulate publishing for testing and dry-run CLI execution."""
        simulated_ig = f"mock_ig_carousel_{int(time.time())}"
        simulated_fb = f"{channel.fb_page_id or 'mock_page'}_post_{int(time.time())}"

        logger.info(f"DRY-RUN: Simulated publishing {len(image_paths)} cards to {channel.brand_handle}")
        logger.info(f"DRY-RUN: Simulated Instagram Carousel ID: {simulated_ig}")
        logger.info(f"DRY-RUN: Simulated Facebook Post ID: {simulated_fb}")

        return PublishResult(
            channel_key=channel.key,
            is_dry_run=dry_run,
            instagram_post_id=simulated_ig,
            facebook_post_id=simulated_fb,
            published_images=[str(p) for p in image_paths],
            status="SIMULATED_SUCCESS",
            details={
                "dry_run": True,
                "caption_preview": carousel.caption[:120] + "...",
                "slide_count": len(image_paths),
            },
        )

    def _publish_instagram_carousel(
        self, ig_user_id: str, access_token: str, image_urls: List[str], caption: str
    ) -> str:
        """Publish Instagram carousel with 4-step Graph API container workflow."""
        logger.info("Creating Instagram carousel item containers...")
        item_container_ids = []

        # Step 1: Create individual item containers
        for url in image_urls:
            res = requests.post(
                f"{GRAPH_BASE_URL}/{ig_user_id}/media",
                data={
                    "image_url": url,
                    "is_carousel_item": "true",
                    "access_token": access_token,
                },
                timeout=30,
            )
            res.raise_for_status()
            item_container_ids.append(res.json()["id"])

        # Step 2: Create main carousel container
        logger.info("Creating main Instagram carousel container...")
        res = requests.post(
            f"{GRAPH_BASE_URL}/{ig_user_id}/media",
            data={
                "media_type": "CAROUSEL",
                "children": ",".join(item_container_ids),
                "caption": caption,
                "access_token": access_token,
            },
            timeout=30,
        )
        res.raise_for_status()
        carousel_container_id = res.json()["id"]

        # Step 3: Poll status until FINISHED
        logger.info(f"Polling container status {carousel_container_id}...")
        self._wait_for_container_ready(carousel_container_id, access_token)

        # Step 4: Publish carousel
        logger.info(f"Publishing container {carousel_container_id}...")
        pub_res = requests.post(
            f"{GRAPH_BASE_URL}/{ig_user_id}/media_publish",
            data={
                "creation_id": carousel_container_id,
                "access_token": access_token,
            },
            timeout=30,
        )
        pub_res.raise_for_status()
        return pub_res.json()["id"]

    def _wait_for_container_ready(
        self, container_id: str, access_token: str, max_retries: int = 10
    ):
        """Poll container status until ready for publishing."""
        for _ in range(max_retries):
            res = requests.get(
                f"{GRAPH_BASE_URL}/{container_id}",
                params={"fields": "status_code", "access_token": access_token},
                timeout=15,
            )
            if res.status_code == 200:
                status = res.json().get("status_code")
                if status == "FINISHED":
                    return
                elif status == "ERROR":
                    raise RuntimeError(f"Instagram media container {container_id} failed processing.")
            time.sleep(2)
        raise TimeoutError(f"Instagram container {container_id} timed out before finishing.")

    def _publish_facebook_photos(
        self, page_id: str, access_token: str, image_paths: List[Path], message: str
    ) -> str:
        """Upload unpublished images and create multi-photo Facebook feed post."""
        photo_ids = []
        for p in image_paths:
            with open(p, "rb") as f:
                res = requests.post(
                    f"{GRAPH_BASE_URL}/{page_id}/photos",
                    data={"published": "false", "access_token": access_token},
                    files={"source": f},
                    timeout=45,
                )
                res.raise_for_status()
                photo_ids.append(res.json()["id"])

        attached_media = [{"media_fbid": pid} for pid in photo_ids]
        import json
        res = requests.post(
            f"{GRAPH_BASE_URL}/{page_id}/feed",
            data={
                "message": message,
                "attached_media": json.dumps(attached_media),
                "access_token": access_token,
            },
            timeout=30,
        )
        res.raise_for_status()
        return res.json()["id"]
