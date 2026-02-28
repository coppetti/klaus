
import os
import httpx
import asyncio

async def test_kimi():
    api_key = os.getenv("KIMI_API_KEY")
    if not api_key:
        print("❌ No KIMI_API_KEY found")
        return

    print(f"Testing Kimi with key: {api_key[:10]}...")
    
    url = "https://api.moonshot.cn/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "kimi-k2-0711",
        "messages": [{"role": "user", "content": "olá"}],
        "temperature": 0.7
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Err: {e}")

if __name__ == "__main__":
    asyncio.run(test_kimi())
