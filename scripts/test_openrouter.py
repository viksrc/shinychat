import os
from dotenv import load_dotenv
import httpx

# Load environment variables from .env file
load_dotenv('/Users/vivek/projects/shiny/.env')

# Get API key from environment variables
API_KEY = os.getenv('OPENROUTER_API_KEY')

async def test_openrouter():
    if not API_KEY:
        print("Error: OPENROUTER_API_KEY not found in environment variables")
        return

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": "Hello, this is a test message. Please respond with 'API test successful' if you receive this."}
        ]
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                print("✅ API Key is valid!")
                print("Response:", response.json())
            else:
                print(f"❌ Error: {response.status_code}")
                print("Response:", response.text)
                
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_openrouter())
