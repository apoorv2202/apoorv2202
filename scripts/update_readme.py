import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests


USERNAME = "apoorv2202"
README = "README.md"
SVG_PATH = "assets/github-activity.svg"

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


def github_graphql(query):
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN is required to generate the contribution graph."
        )

    response = requests.post(
        "https://api.github.com/graphql",
        json={"query": query},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        timeout=30
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


def get_contributions():

    query = """
    query {
      user(login: "apoorv2202") {
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

    data = github_graphql(query)

    return (
        data["user"]
        ["contributionsCollection"]
        ["contributionCalendar"]
    )


def generate_svg(calendar):

    weeks = calendar["weeks"]

    cell = 12
    gap = 3

    left = 42
    top = 38

    width = left + (len(weeks) * (cell + gap)) + 10
    height = 7 * (cell + gap) + top + 25

    max_count = max(
        day["contributionCount"]
        for week in weeks
        for day in week["contributionDays"]
    )

    if max_count == 0:
        max_count = 1

    def level(count):

        if count == 0:
            return "#0d1117"

        ratio = count / max_count

        if ratio <= 0.25:
            return "#0e4429"

        if ratio <= 0.50:
            return "#006d32"

        if ratio <= 0.75:
            return "#26a641"

        return "#39d353"

    svg = []

    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
    )

    svg.append(
        '<rect width="100%" height="100%" fill="#0d1117"/>'
    )

    svg.append(
        '<text x="15" y="22" '
        'font-family="Arial, sans-serif" '
        'font-size="16" font-weight="600" '
        'fill="#f0f6fc">GitHub Activity</text>'
    )

    days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    for i, day in enumerate(days):

        if i % 2 == 1:

            y = top + i * (cell + gap) + 10

            svg.append(
                f'<text x="8" y="{y}" '
                'font-family="Arial, sans-serif" '
                'font-size="9" fill="#8b949e">'
                f'{day}</text>'
            )

    ist = ZoneInfo("Asia/Kolkata")

    for week_index, week in enumerate(weeks):

        x = left + week_index * (cell + gap)

        for day in week["contributionDays"]:

            date_str = day["date"]
            count = day["contributionCount"]

            date_obj = datetime.strptime(
                date_str,
                "%Y-%m-%d"
            ).replace(
                tzinfo=ZoneInfo("UTC")
            ).astimezone(ist)

            weekday = date_obj.weekday()

            x_pos = x
            y_pos = top + weekday * (cell + gap)

            fill = level(count)

            svg.append(
                f'<rect x="{x_pos}" y="{y_pos}" '
                f'width="{cell}" height="{cell}" '
                f'rx="2" ry="2" fill="{fill}">'
                f'<title>{date_str}: '
                f'{count} contribution(s)</title>'
                f'</rect>'
            )

    svg.append(
        f'<text x="{left}" y="{height - 8}" '
        'font-family="Arial, sans-serif" '
        'font-size="9" fill="#8b949e">'
        f'{calendar["totalContributions"]} contributions'
        '</text>'
    )

    svg.append("</svg>")

    os.makedirs(
        os.path.dirname(SVG_PATH),
        exist_ok=True
    )

    with open(
        SVG_PATH,
        "w",
        encoding="utf-8"
    ) as file:

        file.write("\n".join(svg))


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

    calendar = get_contributions()

    generate_svg(calendar)

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

    print("README and GitHub activity graph updated successfully.")


if __name__ == "__main__":
    main()
