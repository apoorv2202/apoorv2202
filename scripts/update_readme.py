import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests


USERNAME = "apoorv2202"
README = "README.md"
GRAPH_SVG = "github-activity.svg"

GITHUB_API = "https://api.github.com"
GITHUB_GRAPHQL = "https://api.github.com/graphql"


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


def graphql_request(query, variables):
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN is required to generate the GitHub contribution graph."
        )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        GITHUB_GRAPHQL,
        headers=headers,
        json={
            "query": query,
            "variables": variables
        },
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    if "errors" in data:
        raise RuntimeError(data["errors"])

    return data["data"]


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


def get_contribution_data():
    query = """
    query($username: String!) {
      user(login: $username) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
              }
            }
          }
        }
      }
    }
    """

    data = graphql_request(
        query,
        {"username": USERNAME}
    )

    return data["user"]["contributionsCollection"]["contributionCalendar"]


def contribution_level(count, max_count):
    if count == 0:
        return 0

    if max_count <= 0:
        return 1

    ratio = count / max_count

    if ratio <= 0.25:
        return 1
    elif ratio <= 0.50:
        return 2
    elif ratio <= 0.75:
        return 3
    else:
        return 4


def generate_github_graph():
    calendar = get_contribution_data()

    weeks = calendar["weeks"]

    all_counts = [
        day["contributionCount"]
        for week in weeks
        for day in week["contributionDays"]
    ]

    max_count = max(all_counts, default=0)

    cell_size = 12
    cell_gap = 3
    step = cell_size + cell_gap

    left_margin = 38
    top_margin = 35

    graph_width = (
        left_margin
        + len(weeks) * step
        + 15
    )

    graph_height = (
        top_margin
        + 7 * step
        + 20
    )

    colors = [
        "#161b22",
        "#0e4429",
        "#006d32",
        "#26a641",
        "#39d353"
    ]

    svg = []

    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{graph_width}" height="{graph_height}" '
        f'viewBox="0 0 {graph_width} {graph_height}">'
    )

    # Background
    svg.append(
        f'<rect width="{graph_width}" height="{graph_height}" '
        f'rx="8" fill="#0d1117"/>'
    )

    # Title
    svg.append(
        '<text x="15" y="22" '
        'font-family="Arial, sans-serif" '
        'font-size="15" font-weight="600" '
        'fill="#f0f6fc">GitHub Activity</text>'
    )

    # Day labels
    day_labels = {
        1: "Mon",
        3: "Wed",
        5: "Fri"
    }

    for row, label in day_labels.items():
        y = top_margin + row * step + 10

        svg.append(
            f'<text x="5" y="{y}" '
            'font-family="Arial, sans-serif" '
            'font-size="9" fill="#8b949e">'
            f'{label}</text>'
        )

    # Month labels
    previous_month = None

    for column, week in enumerate(weeks):

        first_day = week["contributionDays"][0]["date"]
        date = datetime.strptime(
            first_day,
            "%Y-%m-%d"
        )

        month = date.strftime("%b")

        if month != previous_month:

            x = left_margin + column * step

            svg.append(
                f'<text x="{x}" y="34" '
                'font-family="Arial, sans-serif" '
                'font-size="9" fill="#8b949e">'
                f'{month}</text>'
            )

            previous_month = month

    # Contribution cells
    for column, week in enumerate(weeks):

        for row, day in enumerate(
            week["contributionDays"]
        ):

            count = day["contributionCount"]

            level = contribution_level(
                count,
                max_count
            )

            x = left_margin + column * step
            y = top_margin + row * step

            tooltip = (
                f'{count} contribution'
                f'{"s" if count != 1 else ""} '
                f'on {day["date"]}'
            )

            svg.append(
                f'<rect x="{x}" y="{y}" '
                f'width="{cell_size}" height="{cell_size}" '
                'rx="2" '
                f'fill="{colors[level]}">'
                f'<title>{tooltip}</title>'
                '</rect>'
            )

    svg.append("</svg>")

    with open(
        GRAPH_SVG,
        "w",
        encoding="utf-8"
    ) as file:

        file.write("\n".join(svg))

    return calendar["totalContributions"]


def main():

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
    # Generate GitHub graph
    # -------------------------

    generate_github_graph()

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

    # -------------------------
    # GitHub Activity Graph
    # -------------------------

    graph_section = """<p align="center">
  <img
    src="./github-activity.svg"
    alt="Apoorv's GitHub Contribution Graph"
  />
</p>"""

    readme = replace_section(
        readme,
        "<!-- GITHUB-GRAPH:START -->",
        "<!-- GITHUB-GRAPH:END -->",
        graph_section
    )

    # -------------------------
    # Metrics
    # -------------------------

    readme = replace_section(
        readme,
        "<!-- GITHUB-METRICS:START -->",
        "<!-- GITHUB-METRICS:END -->",
        metrics
    )

    # -------------------------
    # Repositories
    # -------------------------

    readme = replace_section(
        readme,
        "<!-- REPOSITORIES:START -->",
        "<!-- REPOSITORIES:END -->",
        repository_section.strip()
    )

    # -------------------------
    # Activity
    # -------------------------

    readme = replace_section(
        readme,
        "<!-- ACTIVITY:START -->",
        "<!-- ACTIVITY:END -->",
        activity
    )

    # -------------------------
    # Profile updated
    # -------------------------

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
    print("GitHub contribution graph generated successfully.")


if __name__ == "__main__":
    main()
