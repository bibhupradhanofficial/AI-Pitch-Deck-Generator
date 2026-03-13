import asyncio
import os
from dotenv import load_dotenv

# Path to the .env in backend
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from agents import pitch_agent

async def test():
    print("Testing generate_pitch_content with env loaded...")
    print(f"GEMINI_API_KEY: {os.getenv('GEMINI_API_KEY')[:5]}...")
    try:
        res = await pitch_agent.generate_pitch_content(
            "a startup that provides AI-driven personal finance advice",
            None,
            None,
            "professional",
        )
        # Check if it's the mock content or real
        if "slides" in res:
            print(f"Success! Generated {len(res['slides'])} slides.")
            if res['slides'][0]['title'] == 'Problem' and "High-value teams" in res['slides'][0]['body'][0]:
                print("Note: This looks like MOCK content.")
            else:
                print("Note: This looks like REAL content!")
            print(f"Chart Specs: {res.get('chart_specs')}")
            print(f"Imagen Prompts: {res.get('imagen_prompts')}")
        else:
            print("Failed: " + str(res))
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
