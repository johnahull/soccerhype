#!/usr/bin/env python3
"""
YouTube Authentication Setup Helper for SoccerHype
Guides users through setting up Google Cloud Console and OAuth 2.0 credentials.
"""

import json
import pathlib
import sys
import webbrowser


CLIENT_SECRETS_FILE = pathlib.Path.cwd() / "client_secrets.json"
EXAMPLE_CLIENT_SECRETS = {
    "installed": {
        "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
        "project_id": "your-project-id",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": "YOUR_CLIENT_SECRET",
        "redirect_uris": ["http://localhost"]
    }
}


def print_header(text: str):
    """Print formatted header"""
    print(f"\n{'=' * 70}")
    print(f"  {text}")
    print(f"{'=' * 70}\n")


def print_step(step_num: int, title: str):
    """Print formatted step title"""
    print(f"\n[Step {step_num}] {title}")
    print("-" * 70)


def open_browser(url: str):
    """Open URL in browser with user confirmation"""
    print(f"\n🔗 Opening: {url}")
    choice = input("   Press Enter to open in browser (or 'n' to skip): ").strip().lower()
    if choice != 'n':
        webbrowser.open(url)
        return True
    return False


def main():
    """Guide user through YouTube API setup"""

    print_header("SoccerHype - YouTube Upload Setup")

    print("This setup wizard will help you configure YouTube uploads for SoccerHype.")
    print("You'll need to create a Google Cloud project and OAuth 2.0 credentials.")
    print("\nEstimated time: 10-15 minutes")

    choice = input("\nContinue? (y/n): ").strip().lower()
    if choice != 'y':
        print("Setup cancelled.")
        sys.exit(0)

    # Step 1: Google Cloud Console
    print_step(1, "Create Google Cloud Project")
    print("""
1. Go to Google Cloud Console: https://console.cloud.google.com/
2. Click 'Select a Project' → 'New Project'
3. Enter project name: 'SoccerHype YouTube Uploader' (or your choice)
4. Click 'Create'
5. Wait for project creation to complete
    """)

    open_browser("https://console.cloud.google.com/projectcreate")
    input("\n✅ Press Enter when you've created your project...")

    # Step 2: Enable YouTube API
    print_step(2, "Enable YouTube Data API v3")
    print("""
1. In Google Cloud Console, ensure your project is selected
2. Go to 'APIs & Services' → 'Library'
3. Search for 'YouTube Data API v3'
4. Click on it and press 'Enable'
5. Wait for API to be enabled
    """)

    open_browser("https://console.cloud.google.com/apis/library/youtube.googleapis.com")
    input("\n✅ Press Enter when you've enabled the API...")

    # Step 3: Configure OAuth Consent Screen
    print_step(3, "Configure OAuth Consent Screen")
    print("""
1. Go to 'APIs & Services' → 'OAuth consent screen'
2. Select 'External' user type → Click 'Create'
3. Fill in required fields:
   - App name: 'SoccerHype'
   - User support email: (your email)
   - Developer contact: (your email)
4. Click 'Save and Continue'
5. On 'Scopes' page, click 'Save and Continue' (no changes needed)
6. On 'Test users' page, add your email as a test user
7. Click 'Save and Continue'
8. Review and click 'Back to Dashboard'
    """)

    open_browser("https://console.cloud.google.com/apis/credentials/consent")
    input("\n✅ Press Enter when you've configured the consent screen...")

    # Step 4: Create OAuth Client ID
    print_step(4, "Create OAuth 2.0 Client ID")
    print("""
1. Go to 'APIs & Services' → 'Credentials'
2. Click 'Create Credentials' → 'OAuth client ID'
3. Application type: Select 'Desktop app'
4. Name: 'SoccerHype Desktop Client'
5. Click 'Create'
6. You'll see a popup with your credentials - keep this open!
    """)

    open_browser("https://console.cloud.google.com/apis/credentials")
    input("\n✅ Press Enter when you've created the OAuth client...")

    # Step 5: Download Credentials
    print_step(5, "Download Client Secrets")
    print("""
1. In the OAuth client popup (or from the Credentials page)
2. Click 'Download JSON' button
3. Save the file to your SoccerHype directory as 'client_secrets.json'

   IMPORTANT: The file should be named exactly: client_secrets.json
              And placed in: """ + str(pathlib.Path.cwd()) + """
    """)

    # Wait for file to exist
    while True:
        if CLIENT_SECRETS_FILE.exists():
            print(f"\n✅ Found client_secrets.json!")

            # Validate JSON structure
            try:
                with open(CLIENT_SECRETS_FILE) as f:
                    data = json.load(f)

                # Check if it's the right structure
                if "installed" in data or "web" in data:
                    print("✅ File structure looks correct!")
                    break
                else:
                    print("⚠️  Warning: File structure doesn't match expected format")
                    choice = input("   Continue anyway? (y/n): ").strip().lower()
                    if choice == 'y':
                        break
            except json.JSONDecodeError:
                print("❌ Error: File is not valid JSON")
                choice = input("   Try again? (y/n): ").strip().lower()
                if choice != 'y':
                    sys.exit(1)
        else:
            choice = input(f"\n⏳ Waiting for {CLIENT_SECRETS_FILE.name}... (Press Enter to check, 'q' to quit): ").strip().lower()
            if choice == 'q':
                print("\nSetup incomplete. You can run this script again later.")
                sys.exit(0)

    # Step 6: Test Authentication
    print_step(6, "Test Authentication")
    print("""
Now we'll test the authentication flow. This will:
1. Open a browser window for you to authorize SoccerHype
2. Ask you to log in with your Google account
3. Request permission to upload videos to YouTube
4. Save authentication tokens for future use

Note: You may see a warning that the app isn't verified. This is normal
      for test apps. Click 'Advanced' → 'Go to SoccerHype (unsafe)' to proceed.
    """)

    choice = input("\nReady to test authentication? (y/n): ").strip().lower()
    if choice == 'y':
        try:
            from youtube_uploader import YouTubeUploader

            print("\n🔐 Starting authentication flow...")
            uploader = YouTubeUploader()

            if uploader.authenticate():
                print("\n" + "=" * 70)
                print("  ✅ SUCCESS! YouTube upload is configured!")
                print("=" * 70)
                print("\nYou can now upload videos using:")
                print("  • Command line: python render_highlight.py --upload-youtube")
                print("  • GUI: Click 'Upload to YouTube' button after rendering")
                print("\nYour credentials are saved securely in:")
                print(f"  {HOME / '.soccerhype' / 'youtube-oauth2.json'}")
            else:
                print("\n❌ Authentication failed. Please review the error messages above.")
                sys.exit(1)

        except ImportError:
            print("\n⚠️  Could not import youtube_uploader module.")
            print("   Make sure you've installed the required dependencies:")
            print("   pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Authentication error: {e}")
            sys.exit(1)
    else:
        print("\nYou can test authentication later by running:")
        print("  python youtube_uploader.py --help")

    # Final instructions
    print("\n" + "=" * 70)
    print("  Setup Complete!")
    print("=" * 70)
    print("""
Important Security Notes:
• Keep client_secrets.json private (it's in .gitignore)
• Don't share your OAuth tokens with anyone
• You can revoke access at: https://myaccount.google.com/permissions

Usage Examples:

1. Upload after rendering (CLI):
   python render_highlight.py --dir athletes/john_doe --upload-youtube

2. Upload existing video:
   python youtube_uploader.py athletes/john_doe/output/final.mp4

3. Upload with custom settings:
   python youtube_uploader.py final.mp4 \\
       --title "John Doe Highlights" \\
       --privacy public \\
       --tags "soccer" "highlights" "midfielder"

4. GUI: Use the 'Upload to YouTube' button in soccerhype_gui.py

Need help? Check CLAUDE.md for full documentation.
    """)


if __name__ == "__main__":
    HOME = pathlib.Path.home()
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(0)
