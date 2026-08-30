#!/usr/bin/env python3

import os
import sys
import json
import requests
from loguru import logger

from dotenv import load_dotenv

load_dotenv()

################
# Configuration
################

BITBUCKET_WORKSPACE = os.environ.get("BITBUCKET_WORKSPACE")
BITBUCKET_REPO_SLUG = os.environ.get("BITBUCKET_REPO_SLUG")


GITHUB_OWNER = os.environ.get("GITHUB_OWNER")
GITHUB_REPO = os.environ.get("GITHUB_REPO")

BITBUCKET_USERNAME = os.environ.get("BITBUCKET_USERNAME")
BITBUCKET_APP_PASSWORD = os.environ.get("BITBUCKET_APP_PASSWORD")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

####################
# API Configuration
####################

BITBUCKET_API = "https://api.bitbucket.org/2.0"
GITHUB_API = "https://api.github.com"

bitbucket_auth = (BITBUCKET_USERNAME, BITBUCKET_APP_PASSWORD)

github_header = {
    "Accept": "application/vnd.github.v3+json",
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28",
}


###################
# Bitbucket Helpers
###################
def get_bitbucket_prs():
    """Yield all open pull requests from Bitbucket."""
    logger.info("Fetching open pull requests from Bitbucket...")

    url = (
        f"{BITBUCKET_API}/repositories/"
        f"{BITBUCKET_WORKSPACE}/{BITBUCKET_REPO_SLUG}/pullrequests"
    )

    logger.debug(url)

    params = {"state": "OPEN", "pagelen": 50}

    while url:
        print("Fetching Bitbucket PRs...")
        response = requests.get(
            url,
            params=params,
            auth=bitbucket_auth,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        # Bitbucket returns the next page as a full URL
        yield from data.get("values", [])

        url = data.get("next")  # Next URL already contains query parameters
        params = None


# ============================================================
# GitHub helpers
# ============================================================

github_headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "X-GitHub-Api-Version": "2026-03-10",
}


def branch_exists(branch):
    """Check whether a branch exists in GitHub."""

    url = f"{GITHUB_API}/repos/" f"{GITHUB_OWNER}/{GITHUB_REPO}/git/ref/heads/{branch}"
    logger.debug(f"Checking if branch exists: {url}")

    response = requests.get(
        url,
        headers=github_headers,
        timeout=30,
    )

    if response.status_code == 404:
        sys.exit(
            f"Branch '{branch}' does not exist in GitHub repository '{GITHUB_OWNER}/{GITHUB_REPO}'"
        )
        return False

    response.raise_for_status()
    return True


def pr_already_exists(head, base):
    """Check if an equivalent GitHub PR already exists."""

    url = f"{GITHUB_API}/repos/" f"{GITHUB_OWNER}/{GITHUB_REPO}/pulls"

    response = requests.get(
        url,
        headers=github_headers,
        params={
            "state": "all",
            "head": f"{GITHUB_OWNER}:{head}",
            "base": base,
        },
        timeout=30,
    )

    response.raise_for_status()

    return len(response.json()) > 0


def create_github_pr(title, body, head, base):
    """Create a Pull Request on GitHub."""

    url = f"{GITHUB_API}/repos/" f"{GITHUB_OWNER}/{GITHUB_REPO}/pulls"

    payload = {
        "title": title,
        "body": body,
        "head": head,
        "base": base,
    }

    response = requests.post(
        url,
        headers=github_headers,
        json=payload,
        timeout=30,
    )
    logger.info(f"Creating GitHub PR: {title} from {head} to {base}")

    response.raise_for_status()

    return response.json()


# ============================================================
# Migration
# ============================================================


def migrate_prs():
    print(
        f"Starting migration:\n"
        f"  Bitbucket: {BITBUCKET_WORKSPACE}/{BITBUCKET_REPO_SLUG}\n"
        f"  GitHub:    {GITHUB_OWNER}/{GITHUB_REPO}\n"
    )

    migrated = 0
    skipped = 0
    failed = 0

    for pr in get_bitbucket_prs():

        pr_id = pr["id"]
        title = pr["title"]

        description = pr.get("description") or ""

        source_branch = pr["source"]["branch"]["name"]
        destination_branch = pr["destination"]["branch"]["name"]

        print()
        print(f"Bitbucket PR #{pr_id}: {title}")
        print(f"  {source_branch} -> {destination_branch}")

        # ----------------------------------------------------
        # Verify source branch
        # ----------------------------------------------------

        if not branch_exists(source_branch):
            print(
                f"  SKIPPED: Source branch "
                f"'{source_branch}' does not exist on GitHub"
            )
            skipped += 1
            continue

        # ----------------------------------------------------
        # Verify destination branch
        # ----------------------------------------------------

        if not branch_exists(destination_branch):
            print(
                f"  SKIPPED: Destination branch "
                f"'{destination_branch}' does not exist on GitHub"
            )
            skipped += 1
            continue

        # ----------------------------------------------------
        # Prevent duplicate migration
        # ----------------------------------------------------

        if pr_already_exists(
            source_branch,
            destination_branch,
        ):
            print("  SKIPPED: Equivalent GitHub PR already exists")
            skipped += 1
            continue

        # ----------------------------------------------------
        # Create GitHub PR
        # ----------------------------------------------------

        body = f"{description}\n\n" "---\n" f"**Migrated from Bitbucket PR #{pr_id}**"

        try:
            github_pr = create_github_pr(
                title=title,
                body=body,
                head=source_branch,
                base=destination_branch,
            )

            # logger.info(f"Created GitHub PR #{github_pr}")

            print(f"  SUCCESS: Created GitHub PR " f"#{github_pr['number']}")

            migrated += 1

        except requests.HTTPError as error:

            print(f"  FAILED: {error.response.status_code} " f"{error.response.text}")

            failed += 1

    print("\nMigration complete")
    print(f"  Migrated: {migrated}")
    print(f"  Skipped:  {skipped}")
    print(f"  Failed:   {failed}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    migrate_prs()
