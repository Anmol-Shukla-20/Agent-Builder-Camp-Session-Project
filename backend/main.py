import os
import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.adk.runners import types
from agent import github_card_agent

# Import tools directly for orchestration to save quota
from mcp_server import scrape_github, analyze_profile, generate_card_html, save_card

app = FastAPI(title="GitHub Dev Card API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()
runner = Runner(
    app_name="GithubDevCard",
    agent=github_card_agent,
    session_service=session_service,
    memory_service=memory_service,
    auto_create_session=True
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
CARDS_DIR = os.path.join(STATIC_DIR, "cards")
os.makedirs(CARDS_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class GenerateRequest(BaseModel):
    username: str
    prompt: str = None

@app.post("/generate")
async def generate_card(request: GenerateRequest):
    username = request.username
    print(f"\n--- Starting generation for: {username} ---")
    
    # 1. Scrape GitHub
    print(f"[1/4] Scraping GitHub for {username}...")
    github_data = await scrape_github(username)
    if "error" in github_data:
        print(f"Error: {github_data['error']}")
        raise HTTPException(status_code=404, detail=github_data["error"])
    print(f"Successfully scraped data for {github_data.get('name')}")

    # Extract theme
    theme = "white"
    if request.prompt:
        for t in ["black", "blue", "green", "yellow", "white"]:
            if t in request.prompt.lower():
                theme = t
                break
    print(f"Requested theme: {theme}")

    # 2. Analyze Profile (Try LLM, Fallback to Local)
    print(f"[2/4] Analyzing profile (Calling Gemini)...")
    analysis_json = {}
    agent_msg = "Generated via AI analysis."
    
    try:
        analysis_prompt = f"Analyze this GitHub profile data: {json.dumps(github_data)}. Use theme: {theme}. Return ONLY JSON."
        new_message = types.Content(role="user", parts=[types.Part(text=analysis_prompt)])
        
        full_text = ""
        # Use a reasonable timeout for the AI call
        async for event in runner.run_async(
            user_id="default_user",
            session_id=f"session_{username}",
            new_message=new_message
        ):
            if event.content and hasattr(event.content, "parts"):
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        full_text += part.text
        
        # Try to extract and parse JSON
        if full_text:
            cleaned = full_text.replace("```json", "").replace("```", "").strip()
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start != -1 and end != 0:
                analysis_json = json.loads(cleaned[start:end])
                print(f"Gemini analysis successful.")
            else:
                raise ValueError("No JSON found in response")
        else:
            raise ValueError("Empty response from Gemini")
            
    except Exception as e:
        print(f"Gemini analysis failed or quota hit: {e}")
        print("Using local fallback analysis...")
        analysis_json = await analyze_profile(github_data, theme)
        agent_msg = f"Generated via local fallback (AI was busy: {str(e)})"

    # Ensure analysis_json is never empty and has required keys
    if not analysis_json or not isinstance(analysis_json, dict):
        analysis_json = await analyze_profile(github_data, theme)
    
    # 3. Generate HTML
    print(f"[3/4] Generating HTML...")
    html_content = await generate_card_html(username, github_data, analysis_json)
    if not html_content:
        print("Error: HTML generation returned nothing")
        raise HTTPException(status_code=500, detail="HTML generation failed")
    print(f"HTML generated ({len(html_content)} bytes)")

    # 4. Save Card
    print(f"[4/4] Saving card...")
    card_rel_path = await save_card(username, html_content)
    print(f"Card saved to: {card_rel_path}")

    print(f"--- Generation Complete for {username} ---\n")

    return {
        "username": username,
        "card_url": card_rel_path,
        "html": html_content,
        "agent_response": agent_msg
    }

@app.get("/card/{username}")
async def get_card(username: str):
    card_path = os.path.join(CARDS_DIR, f"{username}.html")
    if os.path.exists(card_path):
        return FileResponse(card_path)
    else:
        raise HTTPException(status_code=404, detail="Card not found")

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

