import aiohttp
import os
import asyncio
import sys
from dotenv import load_dotenv
load_dotenv()

api_url = os.getenv('BOT_API_URL')
api_key = os.getenv('BOT_API_KEY')
bot_id = os.getenv('BOT_ID')

async def api_request(endpoint, request_type="get", payload=None):
    headers = {
        "X-Api-Key": api_key,
        "X-Bot-ID": bot_id
    }
    if api_url and endpoint:
        full_url = api_url + endpoint + '/'
    else:
        full_url = None
        print(f"Missing api_url: {api_url} or endpoint: {endpoint}")
        return

    async with aiohttp.ClientSession() as session:
        try:
            if payload:
                headers.update(payload)
            if request_type == "get":
                async with session.get(full_url, headers=headers) as response:
                    response_json = await handle_response(response)
            elif request_type == "post":
                async with session.post(full_url, headers=headers, json=payload) as response:
                    response_json = await handle_response(response)
            elif request_type == "delete":
                async with session.delete(full_url, headers=headers) as response:
                    response_json = await handle_response(response)
            else:
                print(f"Unsupported request type: {request_type}")
                return

            print("Response:", response_json)
            return response_json
        except aiohttp.ClientError as e:
            print(f"HTTP request failed: {e}")
        except ValueError as e:
            print(f"ValueError: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

async def handle_response(response):
    if response.headers['Content-Type'] == 'application/json':
        return await response.json()
    else:
        content = await response.text()
        raise ValueError(f"Unexpected content type: {response.headers['Content-Type']}. Response: {content}")

async def main():
    if len(sys.argv) < 2:
        print("Usage: api.py endpoint")
        sys.exit(1)
    endpoint = sys.argv[1]
    await api_request(endpoint=endpoint)

if __name__ == "__main__":
    asyncio.run(main())
