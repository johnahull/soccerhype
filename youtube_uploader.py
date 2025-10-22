#!/usr/bin/env python3
"""
YouTube Uploader Module for SoccerHype
Handles OAuth 2.0 authentication and video uploads to YouTube.
"""

import argparse
import http.client
import httplib2
import json
import os
import pathlib
import random
import sys
import time
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# YouTube API settings
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# OAuth credentials location (outside repo for security)
HOME = pathlib.Path.home()
SOCCERHYPE_CONFIG_DIR = HOME / ".soccerhype"
TOKEN_FILE = SOCCERHYPE_CONFIG_DIR / "youtube-oauth2.json"
CLIENT_SECRETS_FILE = pathlib.Path.cwd() / "client_secrets.json"

# Retry settings
RETRIABLE_EXCEPTIONS = (
    httplib2.HttpLib2Error,
    IOError,
    http.client.NotConnected,
    http.client.IncompleteRead,
    http.client.ImproperConnectionState,
    http.client.CannotSendRequest,
    http.client.CannotSendHeader,
    http.client.ResponseNotReady,
    http.client.BadStatusLine,
)

RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
MAX_RETRIES = 10


class YouTubeUploader:
    """Handles YouTube video uploads with OAuth 2.0 authentication"""

    def __init__(self, client_secrets_path: Optional[pathlib.Path] = None):
        """Initialize uploader with optional custom client secrets path"""
        self.client_secrets = client_secrets_path or CLIENT_SECRETS_FILE
        self.youtube = None

    def authenticate(self) -> bool:
        """
        Authenticate with YouTube API using OAuth 2.0.
        Returns True if successful, False otherwise.
        """
        if not self.client_secrets.exists():
            print(f"❌ Client secrets file not found: {self.client_secrets}")
            print("   Run 'python setup_youtube_auth.py' to set up authentication")
            return False

        # Ensure config directory exists
        SOCCERHYPE_CONFIG_DIR.mkdir(exist_ok=True)

        credentials = None

        # Load existing credentials if available
        if TOKEN_FILE.exists():
            try:
                credentials = Credentials.from_authorized_user_file(
                    str(TOKEN_FILE), [YOUTUBE_UPLOAD_SCOPE]
                )
            except Exception as e:
                print(f"⚠️  Error loading credentials: {e}")
                credentials = None

        # Refresh or obtain new credentials
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                    print("🔄 Refreshed authentication token")
                except Exception as e:
                    print(f"⚠️  Error refreshing token: {e}")
                    credentials = None

            if not credentials:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.client_secrets), [YOUTUBE_UPLOAD_SCOPE]
                    )
                    credentials = flow.run_local_server(port=0)
                    print("✅ Authentication successful")
                except Exception as e:
                    print(f"❌ Authentication failed: {e}")
                    return False

            # Save credentials for future use
            try:
                with open(TOKEN_FILE, "w") as token:
                    token.write(credentials.to_json())
                print(f"💾 Saved credentials to {TOKEN_FILE}")
            except Exception as e:
                print(f"⚠️  Warning: Could not save credentials: {e}")

        # Build YouTube service
        try:
            self.youtube = build(
                YOUTUBE_API_SERVICE_NAME,
                YOUTUBE_API_VERSION,
                credentials=credentials,
            )
            return True
        except Exception as e:
            print(f"❌ Failed to build YouTube service: {e}")
            return False

    def upload_video(
        self,
        video_path: pathlib.Path,
        title: str,
        description: str = "",
        tags: Optional[list[str]] = None,
        category_id: str = "17",  # Sports category
        privacy_status: str = "unlisted",  # public, unlisted, or private
        progress_callback=None,
    ) -> Optional[str]:
        """
        Upload video to YouTube with metadata.
        Returns video ID if successful, None otherwise.

        Args:
            video_path: Path to video file
            title: Video title
            description: Video description
            tags: List of tags/keywords
            category_id: YouTube category (17 = Sports)
            privacy_status: 'public', 'unlisted', or 'private'
            progress_callback: Optional callback function(bytes_uploaded, total_bytes)
        """
        if not self.youtube:
            print("❌ Not authenticated. Call authenticate() first.")
            return None

        if not video_path.exists():
            print(f"❌ Video file not found: {video_path}")
            return None

        # Prepare metadata
        body = {
            "snippet": {
                "title": title[:100],  # YouTube max 100 chars
                "description": description[:5000],  # YouTube max 5000 chars
                "tags": tags or [],
                "categoryId": category_id,
            },
            "status": {"privacyStatus": privacy_status},
        }

        # Prepare media upload
        media = MediaFileUpload(
            str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4"
        )

        print(f"\n🎬 Uploading video: {video_path.name}")
        print(f"   Title: {title}")
        print(f"   Privacy: {privacy_status}")

        # Execute upload with retry logic
        try:
            request = self.youtube.videos().insert(
                part=",".join(body.keys()), body=body, media_body=media
            )

            response = None
            retry = 0

            while response is None:
                try:
                    status, response = request.next_chunk()
                    if status and progress_callback:
                        progress_callback(status.resumable_progress, status.total_size)
                    elif status:
                        print(
                            f"   Progress: {int(status.resumable_progress / status.total_size * 100)}%"
                        )
                except HttpError as e:
                    if e.resp.status in RETRIABLE_STATUS_CODES:
                        error = f"HTTP {e.resp.status}: {e.content.decode()}"
                        print(f"⚠️  Retriable error: {error}")
                        retry = self._retry_with_backoff(retry)
                        if retry is None:
                            return None
                    else:
                        print(f"❌ Upload failed: {e}")
                        return None
                except RETRIABLE_EXCEPTIONS as e:
                    print(f"⚠️  Retriable error: {e}")
                    retry = self._retry_with_backoff(retry)
                    if retry is None:
                        return None

            if "id" in response:
                video_id = response["id"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                print(f"\n✅ Upload successful!")
                print(f"   Video ID: {video_id}")
                print(f"   URL: {video_url}")
                return video_id
            else:
                print(f"❌ Upload failed: {response}")
                return None

        except Exception as e:
            print(f"❌ Upload error: {e}")
            return None

    def _retry_with_backoff(self, retry_count: int) -> Optional[int]:
        """
        Implement exponential backoff for retries.
        Returns next retry count or None if max retries exceeded.
        """
        if retry_count >= MAX_RETRIES:
            print(f"❌ Maximum retries ({MAX_RETRIES}) exceeded")
            return None

        retry_count += 1
        sleep_time = random.random() * (2**retry_count)
        print(f"   Retrying in {sleep_time:.1f} seconds... (attempt {retry_count}/{MAX_RETRIES})")
        time.sleep(sleep_time)
        return retry_count


def generate_title_from_project(project_data: dict) -> str:
    """Generate video title from project.json data"""
    player = project_data.get("player", {})
    name = player.get("name", "Player")
    grad_year = player.get("grad_year", "")
    position = player.get("position", "")

    parts = [name]
    if grad_year:
        parts.append(f"Class of {grad_year}")
    if position:
        parts.append(position)

    parts.append("Highlight Video")

    return " - ".join(parts)


def generate_description_from_project(project_data: dict) -> str:
    """Generate video description from project.json data"""
    player = project_data.get("player", {})
    name = player.get("name", "Player")
    position = player.get("position", "")
    grad_year = player.get("grad_year", "")
    club_team = player.get("club_team", "")
    high_school = player.get("high_school", "")
    height_weight = player.get("height_weight", "")
    gpa = player.get("gpa", "")

    lines = [f"{name} - Highlight Video"]

    if position and grad_year:
        lines.append(f"{position} | Class of {grad_year}")
    elif position:
        lines.append(f"Position: {position}")
    elif grad_year:
        lines.append(f"Class of {grad_year}")

    lines.append("")  # Blank line

    if club_team:
        lines.append(f"Club Team: {club_team}")
    if high_school:
        lines.append(f"High School: {high_school}")
    if height_weight:
        lines.append(f"Height/Weight: {height_weight}")
    if gpa:
        lines.append(f"GPA: {gpa}")

    lines.append("")
    lines.append("Created with SoccerHype")

    return "\n".join(lines)


def main():
    """CLI for testing YouTube upload functionality"""
    parser = argparse.ArgumentParser(
        description="Upload highlight video to YouTube"
    )
    parser.add_argument("video", type=str, help="Path to video file")
    parser.add_argument("--title", type=str, help="Video title")
    parser.add_argument("--description", type=str, default="", help="Video description")
    parser.add_argument(
        "--tags", type=str, nargs="+", help="Video tags (space-separated)"
    )
    parser.add_argument(
        "--privacy",
        type=str,
        choices=["public", "unlisted", "private"],
        default="unlisted",
        help="Privacy status (default: unlisted)",
    )
    parser.add_argument(
        "--project",
        type=str,
        help="Path to project.json (auto-generates title/description)",
    )

    args = parser.parse_args()

    video_path = pathlib.Path(args.video)
    if not video_path.exists():
        print(f"❌ Video file not found: {video_path}")
        sys.exit(1)

    # Auto-generate metadata from project.json if provided
    title = args.title
    description = args.description

    if args.project:
        project_path = pathlib.Path(args.project)
        if project_path.exists():
            try:
                project_data = json.loads(project_path.read_text())
                if not title:
                    title = generate_title_from_project(project_data)
                if not description:
                    description = generate_description_from_project(project_data)
            except Exception as e:
                print(f"⚠️  Could not read project file: {e}")

    if not title:
        title = video_path.stem

    # Initialize uploader
    uploader = YouTubeUploader()

    # Authenticate
    if not uploader.authenticate():
        sys.exit(1)

    # Upload video
    video_id = uploader.upload_video(
        video_path=video_path,
        title=title,
        description=description,
        tags=args.tags,
        privacy_status=args.privacy,
    )

    if video_id:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
