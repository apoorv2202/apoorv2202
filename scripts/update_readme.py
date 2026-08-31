import os
import re
from datetime import datetime, timezone

import requests


USERNAME = "apoorv2202"
LEETCODE_USERNAME = "_apoorv10"
README = "README.md"

GITHUB_API = "https://api.github.com"
LEETCODE_API = "https://leetcode.com/graphql"


# --------------------------------------------------
# GitHub API
# --------------------------------------------------

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


# --------------------------------------------------
# LeetCode API
# --------------------------------------------------

def get_leetcode_stats():
    query = """
    query getUserProfile($username: String!) {
        matchedUser(username: $username) {
            submitStats {
                acSubmissionNum {
                    difficulty
                    count
                }
            }
        }
    }
    """

    response = requests.post(
        LEETCODE_API,
        json={
            "query": query,
            "variables": {
                "username": LEETCODE_USERNAME
            }
        },
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        },
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    user = data.get("data", {}).get("matchedUser")

    if not user:
        return None

    stats = user["submitStats"]["acSubmissionNum"]

    result = {}

    for item in stats:
        result[item["difficulty"]] = item["count"]

    return result


# --------------------------------------------------
# Replace README sections
# --------------------------------------------------

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


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    # ==================================================
    # GitHub PROFILE
    # ==================================================

    user = github_request(f"/users/{USERNAME}")

    followers = user["followers"]
    following = user["following"]
    public_repos = user["public_repos"]


    # ==================================================
    # REPOSITORIES
    # ==================================================

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


    # ==================================================
    # GITHUB METRICS
    # ==================================================

    metrics = f"""| Metric | Value |
|---|---:|
| Public Repositories | {public_repos} |
| Followers | {followers} |
| Following | {following} |
| Total Stars | {total_stars} |
| Total Forks | {total_forks} |"""


    # ==================================================
    # LATEST REPOSITORIES
    # ==================================================

    repository_section = ""

    for repo in latest_repos:

        name = repo["name"]

        description = (
            repo["description"]
            or "No description provided."
        )

        url = repo["html_url"]

        repository_section += (
            f"- **[{name}]({url})** — {description}\n"
        )


    # ==================================================
    # GITHUB RECENT ACTIVITY
    # ==================================================

    events = github_request(
        f"/users/{USERNAME}/events/public?per_page=20"
    )

    activity = ""

    activity_count = 0

    for event in events:

        if activity_count >= 5:
            break

        event_type = event["type"]

        repo = event["repo"]["name"]

        if event_type == "PushEvent":

            commits = len(
                event["payload"].get("commits", [])
            )

            activity += (
                f"- 📝 Pushed **{commits} commit(s)** "
                f"to `{repo}`\n"
            )

            activity_count += 1

        elif event_type == "PullRequestEvent":

            action = event["payload"].get(
                "action",
                "updated"
            )

            activity += (
                f"- 🔀 {action.capitalize()} a pull request "
                f"in `{repo}`\n"
            )

            activity_count += 1

        elif event_type == "IssuesEvent":

            action = event["payload"].get(
                "action",
                "updated"
            )

            activity += (
                f"- 🐛 {action.capitalize()} an issue "
                f"in `{repo}`\n"
            )

            activity_count += 1

        elif event_type == "CreateEvent":

            ref_type = event["payload"].get(
                "ref_type",
                "resource"
            )

            activity += (
                f"- 🚀 Created a {ref_type} "
                f"in `{repo}`\n"
            )

            activity_count += 1

        elif event_type == "IssueCommentEvent":

            activity += (
                f"- 💬 Commented on an issue "
                f"in `{repo}`\n"
            )

            activity_count += 1

    if not activity:

        activity = "- No recent public activity."


    # ==================================================
    # LEETCODE STATISTICS
    # ==================================================

    leetcode_stats = get_leetcode_stats()

    if leetcode_stats:

        easy = leetcode_stats.get("Easy", 0)
        medium = leetcode_stats.get("Medium", 0)
        hard = leetcode_stats.get("Hard", 0)

        total = easy + medium + hard

        leetcode_section = f"""| Difficulty | Solved |
|---|---:|
| 🟢 Easy | {easy} |
| 🟡 Medium | {medium} |
| 🔴 Hard | {hard} |
| **Total** | **{total}** |"""

    else:

        leetcode_section = (
            "Unable to fetch LeetCode statistics."
        )


    # ==================================================
    # LAST UPDATED
    # ==================================================

    now = datetime.now(timezone.utc)

    updated = now.astimezone().strftime(
        "%B %d, %Y · %I:%M %p %Z"
    )


    # ==================================================
    # READ README
    # ==================================================

    with open(
        README,
        "r",
        encoding="utf-8"
    ) as file:

        readme = file.read()


    # ==================================================
    # UPDATE GITHUB METRICS
    # ==================================================

    readme = replace_section(
        readme,
        "<!-- GITHUB-METRICS:START -->",
        "<!-- GITHUB-METRICS:END -->",
        metrics
    )


    # ==================================================
    # UPDATE REPOSITORIES
    # ==================================================

    readme = replace_section(
        readme,
        "<!-- REPOSITORIES:START -->",
        "<!-- REPOSITORIES:END -->",
        repository_section.strip()
    )


    # ==================================================
    # UPDATE ACTIVITY
    # ==================================================

    readme = replace_section(
        readme,
        "<!-- ACTIVITY:START -->",
        "<!-- ACTIVITY:END -->",
        f"### Recent GitHub Activity\n\n{activity.strip()}"
    )


    # ==================================================
    # UPDATE LEETCODE
    # ==================================================

    readme = replace_section(
        readme,
        "<!-- LEETCODE-STATS:START -->",
        "<!-- LEETCODE-STATS:END -->",
        leetcode_section
    )


    # ==================================================
    # UPDATE PROFILE TIMESTAMP
    # ==================================================

    readme = replace_section(
        readme,
        "<!-- PROFILE-UPDATED:START -->",
        "<!-- PROFILE-UPDATED:END -->",
        f"*Last automatically updated: {updated}*"
    )


    # ==================================================
    # WRITE README
    # ==================================================

    with open(
        README,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(readme)


    print("README updated successfully.")

    if leetcode_stats:

        print(
            f"LeetCode: "
            f"{leetcode_stats.get('Easy', 0)} Easy, "
            f"{leetcode_stats.get('Medium', 0)} Medium, "
            f"{leetcode_stats.get('Hard', 0)} Hard"
        )


if __name__ == "__main__":
    main()
