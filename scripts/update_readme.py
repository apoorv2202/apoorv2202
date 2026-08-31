import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests


USERNAME = "apoorv2202"
README = "README.md"
SVG_PATH = "assets/github-activity.svg"

GITHUB_API = "https://api.github.com/graphql"


def github_graphql(query, variables=None):
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN environment variable is required."
        )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        GITHUB_API,
        json={
            "query": query,
            "variables": variables or {},
        },
        headers=headers,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if "errors" in data:
        raise RuntimeError(data["errors"])

    return data["data"]


def github_request(endpoint):
    token = os.getenv("GITHUB_TOKEN")

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(
        f"https://api.github.com{endpoint}",
        headers=headers,
        timeout=20,
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
        flags=re.DOTALL,
    )


def generate_github_graph():
    query = """
    query($username: String!) {
      user(login: $username) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """

    data = github_graphql(
        query,
        {"username": USERNAME},
    )

    calendar = data["user"]["contributionsCollection"]["contributionCalendar"]

    weeks = calendar["weeks"]
    total = calendar["totalContributions"]

    cell_size = 12
    cell_gap = 3
    step = cell_size + cell_gap

    left_padding = 40
    top_padding = 35

    graph_width = (
        left_padding
        + len(weeks) * step
        + 10
    )

    graph_height = 180

    # Black background with green contribution levels.
    background = "#0d1117"

    levels = [
        "#161b22",
        "#0e4429",
        "#006d32",
        "#26a641",
        "#39d353",
    ]

    svg = []

    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{graph_width}" '
        f'height="{graph_height}" '
        f'viewBox="0 0 {graph_width} {graph_height}">'
    )

    svg.append(
        f'<rect width="100%" height="100%" rx="10" fill="{background}"/>'
    )

    # Title
    svg.append(
        '<text x="20" y="25" '
        'fill="#f0f6fc" '
        'font-family="Arial, sans-serif" '
        'font-size="16" '
        'font-weight="600">'
        'GitHub Activity'
        '</text>'
    )

    # Day labels
    day_labels = [
        ("Mon", 1),
        ("Wed", 3),
        ("Fri", 5),
    ]

    for label, row in day_labels:
        y = top_padding + row * step + 9

        svg.append(
            f'<text x="4" y="{y}" '
            'fill="#8b949e" '
            'font-family="Arial, sans-serif" '
            'font-size="9">'
            f'{label}'
            '</text>'
        )

    # Month labels
    previous_month = None

    for column, week in enumerate(weeks):
        if not week["contributionDays"]:
            continue

        date = week["contributionDays"][0]["date"]

        month = datetime.strptime(
            date,
            "%Y-%m-%d"
        ).strftime("%b")

        if month != previous_month:
            x = left_padding + column * step

            svg.append(
                f'<text x="{x}" y="43" '
                'fill="#8b949e" '
                'font-family="Arial, sans-serif" '
                'font-size="9">'
                f'{month}'
                '</text>'
            )

            previous_month = month

    # Contribution cells
    max_count = max(
        (
            day["contributionCount"]
            for week in weeks
            for day in week["contributionDays"]
        ),
        default=1,
    )

    for column, week in enumerate(weeks):

        for row, day in enumerate(
            week["contributionDays"]
        ):

            count = day["contributionCount"]

            if count == 0:
                level = 0
            elif count <= max_count * 0.25:
                level = 1
            elif count <= max_count * 0.50:
                level = 2
            elif count <= max_count * 0.75:
                level = 3
            else:
                level = 4

            x = left_padding + column * step
            y = top_padding + row * step

            svg.append(
                f'<rect '
                f'x="{x}" '
                f'y="{y}" '
                f'width="{cell_size}" '
                f'height="{cell_size}" '
                f'rx="2" '
                f'fill="{levels[level]}">'
                f'<title>{day["date"]}: '
                f'{count} contributions</title>'
                f'</rect>'
            )

    # Total contributions
    svg.append(
        f'<text x="20" y="170" '
        'fill="#8b949e" '
        'font-family="Arial, sans-serif" '
        'font-size="10">'
        f'{total} contributions in the last year'
        '</text>'
    )

    svg.append("</svg>")

    os.makedirs(
        os.path.dirname(SVG_PATH),
        exist_ok=True,
    )

    with open(
        SVG_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        file.write("\n".join(svg))

    print(
        f"GitHub activity graph generated: {SVG_PATH}"
    )


def main():

    # -------------------------
    # Generate GitHub graph
    # -------------------------

    generate_github_graph()

    # -------------------------
    # GitHub profile
    # -------------------------

    user = github_request(
        f"/users/{USERNAME}"
    )

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
        description = (
            repo["description"]
            or "No description provided."
        )

        url = repo["html_url"]

        repository_section += (
            f"- **[{name}]({url})** — "
            f"{description}\n"
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
        repo = event.get(
            "repo",
            {}
        ).get("name")

        if not repo:
            continue

        if event_type == "PushEvent":

            commit_count = event["payload"].get(
                "size"
            )

            if commit_count is None:
                commit_count = len(
                    event["payload"].get(
                        "commits",
                        []
                    )
                )

            activity_lines.append(
                f"- 📝 Pushed **{commit_count} "
                f"commit(s)** to `{repo}`"
            )

        elif event_type == "PullRequestEvent":

            action = event["payload"].get(
                "action",
                "updated"
            )

            activity_lines.append(
                f"- 🔀 {action.capitalize()} "
                f"a pull request in `{repo}`"
            )

        elif event_type == "IssuesEvent":

            action = event["payload"].get(
                "action",
                "updated"
            )

            activity_lines.append(
                f"- 🐛 {action.capitalize()} "
                f"an issue in `{repo}`"
            )

        elif event_type == "CreateEvent":

            ref_type = event["payload"].get(
                "ref_type",
                "resource"
            )

            activity_lines.append(
                f"- ✨ Created a {ref_type} "
                f"in `{repo}`"
            )

        elif event_type == "DeleteEvent":

            ref_type = event["payload"].get(
                "ref_type",
                "resource"
            )

            activity_lines.append(
                f"- 🗑️ Deleted a {ref_type} "
                f"in `{repo}`"
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
        encoding="utf-8",
    ) as file:

        readme = file.read()

    readme = replace_section(
        readme,
        "<!-- GITHUB-METRICS:START -->",
        "<!-- GITHUB-METRICS:END -->",
        metrics,
    )

    readme = replace_section(
        readme,
        "<!-- REPOSITORIES:START -->",
        "<!-- REPOSITORIES:END -->",
        repository_section.strip(),
    )

    readme = replace_section(
        readme,
        "<!-- ACTIVITY:START -->",
        "<!-- ACTIVITY:END -->",
        activity,
    )

    readme = replace_section(
        readme,
        "<!-- PROFILE-UPDATED:START -->",
        "<!-- PROFILE-UPDATED:END -->",
        f"*Last automatically updated: {updated}*",
    )

    with open(
        README,
        "w",
        encoding="utf-8",
    ) as file:

        file.write(readme)

    print("README updated successfully.")


if __name__ == "__main__":
    main()
