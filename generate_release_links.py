import argparse
import json
import os
import sys
from typing import Dict, List
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, build_opener
from urllib.request import HTTPRedirectHandler as BaseRedirectHandler
from urllib.request import urlopen

REPO_SLUG = "Bigredgeek/SOTN_TTS2KML_Merged"
ASSET_NAMES = ("OpMap.kml", "StratMap.kml", "TacMap.kml")


def extract_release_tag(value: str) -> str:
    """Return the release tag from a tag name or a GitHub release URL."""
    if not value:
        raise ValueError("Release tag cannot be empty")

    candidate = value.strip()
    if not candidate:
        raise ValueError("Release tag cannot be empty")

    if candidate.startswith("http://") or candidate.startswith("https://"):
        parsed = urlparse(candidate)
        if not parsed.path:
            raise ValueError("Release URL does not contain a tag segment")
        candidate = parsed.path

    candidate = candidate.rstrip("/")
    if not candidate:
        raise ValueError("Release tag cannot be empty")

    if "/" in candidate:
        candidate = candidate.split("/")[-1]

    if not candidate:
        raise ValueError("Release tag cannot be empty")

    return candidate


def _github_headers(token: str, accept: str) -> Dict[str, str]:
    headers = {
        "Accept": accept,
        "User-Agent": "github-release-link-generator",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    return headers


def fetch_release_assets(repo_slug: str, release_tag: str, token: str) -> List[dict]:
    url = f"https://api.github.com/repos/{repo_slug}/releases/tags/{release_tag}"
    request = Request(url, headers=_github_headers(token, "application/vnd.github+json"))
    with urlopen(request) as response:
        data = json.load(response)
    return data.get("assets", [])


class _NoRedirectHandler(BaseRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


def fetch_direct_asset_url(asset_url: str, token: str) -> str:
    request = Request(asset_url, headers=_github_headers(token, "application/octet-stream"))
    opener = build_opener(_NoRedirectHandler)
    try:
        with opener.open(request) as response:
            # If the redirect did not trigger, fall back to the final URL.
            return response.geturl()
    except HTTPError as err:
        if err.code in (301, 302, 303, 307, 308):
            location = err.headers.get("Location")
            if location:
                return location
        raise


def resolve_direct_urls(repo_slug: str, release_tag: str, token: str) -> Dict[str, str]:
    assets = fetch_release_assets(repo_slug, release_tag, token)
    lookup = {asset.get("name"): asset for asset in assets if asset.get("name")}
    results: Dict[str, str] = {}

    for asset_name in ASSET_NAMES:
        asset = lookup.get(asset_name)
        if not asset:
            continue
        asset_api_url = asset.get("url")
        if not asset_api_url:
            continue
        try:
            direct_url = fetch_direct_asset_url(asset_api_url, token)
        except HTTPError as err:
            print(
                f"Warning: failed to resolve direct URL for {asset_name}: HTTP {err.code}",
                file=sys.stderr,
            )
            continue
        except URLError as err:
            print(
                f"Warning: network error resolving direct URL for {asset_name}: {err}",
                file=sys.stderr,
            )
            continue
        results[asset_name] = direct_url

    return results


def write_links(target_dir: str, urls: Dict[str, str]) -> str:
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, "github_release_links.txt")

    with open(file_path, "w", encoding="utf-8", newline="\n") as handle:
        for asset in ASSET_NAMES:
            url = urls[asset]
            handle.write(url + "\n")

    return file_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate direct download URLs for release assets."
    )
    parser.add_argument(
        "--repo",
        default=REPO_SLUG,
        help="Repository slug (owner/name). Defaults to Bigredgeek/SOTN_TTS2KML_Merged.",
    )
    parser.add_argument(
        "--token",
        help="GitHub token for API access. If omitted, GITHUB_TOKEN or GH_TOKEN will be used.",
    )
    parser.add_argument(
        "archive_dir",
        help="Output directory where github_release_links.txt will be written.",
    )
    parser.add_argument(
        "release",
        help="Release tag or full GitHub release URL (e.g. SOTN-post-GT4).",
    )
    args = parser.parse_args()

    try:
        tag = extract_release_tag(args.release)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    repo_slug = args.repo

    token = args.token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("Error: GitHub token is required to resolve direct download URLs.", file=sys.stderr)
        return 1

    direct_map = resolve_direct_urls(repo_slug, tag, token)
    missing = [asset for asset in ASSET_NAMES if asset not in direct_map]
    if missing:
        print(
            f"Error: Could not resolve direct URLs for: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 1

    try:
        output_path = write_links(args.archive_dir, direct_map)
    except OSError as exc:
        print(f"Error writing links file: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote release download links to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
