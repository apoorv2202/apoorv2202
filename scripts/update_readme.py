import os
import re
from datetime import datetime, timezone

import requests


USERNAME = "apoorv2202"
README = "README.md"

GITHUB_API = "https://api.github.com"


def github_request(endpoint):
    token = os.getenv("GITHUB_TOKEN")

    headers = {
        "Accept": "application/vnd.github+json"
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(
        f"{GITHUB_API}{endpoint}",
        headers=headers,
        timeout=20
    )

    response.raise_for_status()
    return response.json()


def replace_section(text, start_marker, end_marker, replacement):
    pattern = (
        re.escape(start_marker)
        + r".*?"
        + re.escape(end_marker)
    )

    return re.sub(
        pattern,
        f"{start_marker}\n{replacement}\n{end_marker}",
        text,
        flags=re.DOTALL
    )


def main():

    # -------------------------
    # GitHub profile
    # -------------------------

    user = github_request(f"/users/{USERNAME}")

    followers = user["followers"]
    following = user["following"]
    public_repos = user["public_repos"]

    # -------------------------
    # Repositories
    # -------------------------

    repos = github_request(
        f"/users/{USERNAME}/repos?per_page=100&sort=updated"
    )

    total_stars = sum(repo["stargazers_count"] for repo in repos)
    total_forks = sum(repo["forks_count"] for repo in repos)

    latest_repos = repos[:5]

    # -------------------------
    # Metrics
    # -------------------------

    metrics = f"""| Metric | Value |
|---|---:|
| Public Repositories | {public_repos} |
| Followers | {followers} |
| Following | {following} |
| Total Stars | {total_stars} |
| Total Forks | {total_forks} |"""

    # -------------------------
    # Latest repositories
    # -------------------------

    repository_section = ""

    for repo in latest_repos:

        name = repo["name"]
        description = repo["description"] or "No description provided."
        url = repo["html_url"]

        repository_section += (
            f"- **[{name}]({url})** — {description}\n"
        )

    # -------------------------
    # Recent activity
    # -------------------------

    events = github_request(
        f"/users/{USERNAME}/events/public?per_page=10"
    )

    activity = ""

    for event in events[:5]:

        event_type = event["type"]

        if event_type == "PushEvent":

            repo = event["repo"]["name"]
            commits = len(event["payload"].get("commits", []))

            activity += (
                f"- Pushed **{commits} commit(s)** to "
                f"`{repo}`\n"
            )

        elif event_type == "IssuesEvent":

            repo = event["repo"]["name"]

            activity += (
                f"- Activity on an issue in `{repo}`\n"
            )

        elif event_type == "PullRequestEvent":

            repo = event["repo"]["name"]

            activity += (
                f"- Pull request activity in `{repo}`\n"
            )

        elif event_type == "CreateEvent":

            repo = event["repo"]["name"]

            activity += (
                f"- Created something in `{repo}`\n"
            )

    if not activity:
        activity = "- No recent public activity."

    # -------------------------
    # Last updated
    # -------------------------

    now = datetime.now(timezone.utc)

    updated = now.strftime(
        "%B %d, %Y · %H:%M UTC"
    )

    # -------------------------
    # Update README
    # -------------------------

    with open(README, "r", encoding="utf-8") as file:
        readme = file.read()

    readme = replace_section(
        readme,
        "<!-- GITHUB-METRICS:START -->",
        "<!-- GITHUB-METRICS:END -->",
        metrics
    )

    readme = replace_section(
        readme,
        "<!-- REPOSITORIES:START -->",
        "<!-- REPOSITORIES:END -->",
        repository_section.strip()
    )

    readme = replace_section(
        readme,
        "<!-- ACTIVITY:START -->",
        "<!-- ACTIVITY:END -->",
        activity.strip()
    )

    readme = replace_section(
        readme,
        "<!-- PROFILE-UPDATED:START -->",
        "<!-- PROFILE-UPDATED:END -->",
        f"*Last automatically updated: {updated}*"
    )

    with open(README, "w", encoding="utf-8") as file:
        file.write(readme)

    print("README updated successfully.")


if __name__ == "__main__":
    main()
