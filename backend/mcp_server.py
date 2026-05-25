import os
import json
import httpx
from mcp.server.fastmcp import FastMCP
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("GithubDevCard")

GITHUB_API_BASE = "https://api.github.com"
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

@mcp.tool()
async def scrape_github(username: str):
    """Fetch GitHub statistics for a given username."""
    async with httpx.AsyncClient() as client:
        # Fetch user profile
        user_res = await client.get(f"{GITHUB_API_BASE}/users/{username}")
        if user_res.status_code == 404:
            return {"error": f"User {username} not found"}
        user_res.raise_for_status()
        user_data = user_res.json()

        # Fetch repos
        repos_res = await client.get(f"{GITHUB_API_BASE}/users/{username}/repos?sort=stars&per_page=30")
        repos_res.raise_for_status()
        repos_data = repos_res.json()

    # Sort and take top 6 repos
    top_repos = sorted(repos_data, key=lambda x: x.get("stargazers_count", 0), reverse=True)[:6]
    
    # Process repo data
    processed_repos = []
    languages = {}
    for r in top_repos:
        lang = r.get("language")
        if lang:
            languages[lang] = languages.get(lang, 0) + 1
        processed_repos.append({
            "name": r.get("name"),
            "stars": r.get("stargazers_count"),
            "language": lang,
            "description": r.get("description")
        })

    # Sort languages by frequency
    top_languages = sorted(languages.items(), key=lambda x: x[1], reverse=True)

    return {
        "name": user_data.get("name") or username,
        "bio": user_data.get("bio"),
        "location": user_data.get("location"),
        "public_repos": user_data.get("public_repos"),
        "followers": user_data.get("followers"),
        "avatar_url": user_data.get("avatar_url"),
        "top_repos": processed_repos,
        "most_used_languages": [lang for lang, count in top_languages[:5]]
    }

@mcp.tool()
async def analyze_profile(github_data: dict, requested_theme: str = None):
    """Analyze GitHub profile to determine vibe and theme."""
    languages = github_data.get("most_used_languages", [])
    skills = languages[:3] if languages else ["Coding", "Git", "GitHub"]
    
    # Default to white if theme is not recognized or not provided
    valid_themes = ["black", "blue", "green", "yellow", "white"]
    theme = requested_theme.lower() if requested_theme and requested_theme.lower() in valid_themes else "white"
    
    return {
        "developer_vibe": f"A passionate developer focused on {skills[0] if skills else 'software development'}.",
        "top_skills": skills,
        "fun_fact": f"Has contributed to {github_data.get('public_repos')} public repositories.",
        "card_theme": theme
    }

@mcp.tool()
async def generate_card_html(username: str, github_data: dict, analysis: dict):
    """Generate a self-contained HTML string for the dev card."""
    # Ensure analysis is a dict
    if isinstance(analysis, str):
        try:
            analysis = json.loads(analysis)
        except:
            analysis = {}

    theme = analysis.get("card_theme", "white")
    
    themes = {
        "white": {"bg": "#ffffff", "text": "#24292f", "accent": "#0969da"},
        "black": {"bg": "#0d1117", "text": "#f0f6fc", "accent": "#58a6ff"},
        "blue": {"bg": "#ddf4ff", "text": "#0969da", "accent": "#0969da"},
        "green": {"bg": "#dafbe1", "text": "#1a7f37", "accent": "#1a7f37"},
        "yellow": {"bg": "#fff8c5", "text": "#9a6700", "accent": "#9a6700"}
    }
    
    colors = themes.get(theme, themes["white"])
    
    tag_text = "white"
    if theme == "black":
        tag_text = "black"
        colors["accent"] = "#f0f6fc"
    
    repos_html = "".join([
        f'<div style="margin-bottom: 8px;"><strong>{r["name"]}</strong> (⭐{r["stars"]})<br><small style="opacity: 0.85;">{r["description"] or ""}</small></div>'
        for r in github_data.get("top_repos", [])[:3]
    ])
    
    skills_html = "".join([
        f'<span style="background:{colors["accent"]}; color:{tag_text}; padding: 3px 10px; border-radius: 12px; margin-right: 6px; font-size: 12px; font-weight: 700; border: 1px solid rgba(0,0,0,0.1);">{s}</span>'
        for s in analysis.get("top_skills", [])
    ])

    html = f"""
    <div id="github-card" style="width: 400px; padding: 25px; background: {colors["bg"]}; color: {colors["text"]}; border: 1px solid rgba(0,0,0,0.1); border-radius: 16px; font-family: 'Inter', -apple-system, system-ui, sans-serif; box-shadow: 0 8px 24px rgba(0,0,0,0.12);">
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            <img src="{github_data.get("avatar_url")}" style="width: 64px; height: 64px; border-radius: 50%; border: 2px solid {colors["accent"]}; margin-right: 18px; object-fit: cover;">
            <div>
                <h2 style="margin: 0; font-size: 22px; font-weight: 800; letter-spacing: -0.01em;">{github_data.get("name")}</h2>
                <p style="margin: 0; font-size: 15px; opacity: 0.7; font-weight: 500;">@{username}</p>
            </div>
        </div>
        <p style="font-style: italic; margin-bottom: 18px; font-size: 15px; line-height: 1.5; opacity: 0.9;">"{analysis.get("developer_vibe")}"</p>
        <div style="margin-bottom: 18px; display: flex; flex-wrap: wrap; gap: 6px;">{skills_html}</div>
        <div style="display: flex; gap: 24px; margin-bottom: 20px; font-size: 15px; font-weight: 600;">
            <span><strong>{github_data.get("public_repos")}</strong> Repos</span>
            <span><strong>{github_data.get("followers")}</strong> Followers</span>
        </div>
        <div style="border-top: 1px solid rgba(0,0,0,0.08); padding-top: 15px;">
            <h4 style="margin-top: 0; margin-bottom: 12px; font-size: 16px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.8;">Top Projects</h4>
            {repos_html}
        </div>
        <div style="margin-top: 20px; font-size: 13px; border-top: 1px solid rgba(0,0,0,0.08); padding-top: 10px; opacity: 0.7; display: flex; align-items: flex-start; gap: 8px; line-height: 1.4;">
            <span style="font-size: 16px;">💡</span> <span>{analysis.get("fun_fact")}</span>
        </div>
    </div>
    """
    return html

@mcp.tool()
async def save_card(username: str, html: str):
    """Save the HTML to static/cards/{username}.html."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, "static", "cards", f"{username}.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return f"/static/cards/{username}.html"

if __name__ == "__main__":
    mcp.run()
