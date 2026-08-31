import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests


USERNAME = "apoorv2202"
README = "README.md"

GITHUB_API = "https://api.github.com"


def github_request(endpoint):
    token = os.getenv("GITHUB_TOKEN")

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
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

    total_stars = sum(
        repo["stargazers_count"]
        for repo in repos
    )

    total_forks = sum(
        repo["forks_count"]
        for repo in repos
    )

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
        f"/users/{USERNAME}/events/public?per_page=30"
    )

    activity_lines = []

    for event in events:

        event_type = event["type"]
        repo = event.get("repo", {}).get("name")

        if not repo:
            continue

        if event_type == "PushEvent":

            commit_count = event["payload"].get("size")

            if commit_count is None:
                commit_count = len(
                    event["payload"].get("commits", [])
                )

            activity_lines.append(
                f"- 📝 Pushed **{commit_count} commit(s)** to `{repo}`"
            )

        elif event_type == "PullRequestEvent":

            action = event["payload"].get(
                "action",
                "updated"
            )

            activity_lines.append(
                f"- 🔀 {action.capitalize()} a pull request in `{repo}`"
            )

        elif event_type == "IssuesEvent":

            action = event["payload"].get(
                "action",
                "updated"
            )

            activity_lines.append(
                f"- 🐛 {action.capitalize()} an issue in `{repo}`"
            )

        elif event_type == "CreateEvent":

            ref_type = event["payload"].get(
                "ref_type",
                "resource"
            )

            activity_lines.append(
                f"- ✨ Created a {ref_type} in `{repo}`"
            )

        elif event_type == "DeleteEvent":

            ref_type = event["payload"].get(
                "ref_type",
                "resource"
            )

            activity_lines.append(
                f"- 🗑️ Deleted a {ref_type} in `{repo}`"
            )

        elif event_type == "ForkEvent":

            activity_lines.append(
                f"- 🍴 Forked `{repo}`"
            )

        elif event_type == "WatchEvent":

            activity_lines.append(
                f"- ⭐ Starred `{repo}`"
            )

        if len(activity_lines) >= 5:
            break

    if activity_lines:
        activity = (
            "### Recent GitHub Activity\n\n"
            + "\n".join(activity_lines)
        )
    else:
        activity = (
            "### Recent GitHub Activity\n\n"
            "- No recent public activity."
        )

    # -------------------------
    # Last updated — IST
    # -------------------------

    now = datetime.now(
        ZoneInfo("Asia/Kolkata")
    )

    updated = now.strftime(
        "%B %d, %Y · %I:%M %p IST"
    )

    # -------------------------
    # Update README
    # -------------------------

    with open(
        README,
        "r",
        encoding="utf-8"
    ) as file:

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
        activity
    )

    readme = replace_section(
        readme,
        "<!-- PROFILE-UPDATED:START -->",
        "<!-- PROFILE-UPDATED:END -->",
        f"*Last automatically updated: {updated}*"
    )

    with open(
        README,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(readme)

    print("README updated successfully.")


if __name__ == "__main__":
    main()
