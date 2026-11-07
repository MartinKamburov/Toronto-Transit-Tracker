"""Small FastAPI app for trying out the Metrolinx (GO Transit) Open API.

Run from the project root:
    .venv/bin/uvicorn src.tests.testingConnection:app --reload

Then open http://127.0.0.1:8000/docs to call the endpoints from your browser.
"""

import os
import asyncio

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

load_dotenv()

BASE_URL = "https://api.openmetrolinx.com/OpenDataAPI/api/V1"
API_KEY = os.getenv("GO_TRANSIT_API_KEY")

app = FastAPI(title="GO Transit API Tester")


async def call_go_api(path: str) -> dict:
    """Call a Metrolinx endpoint, e.g. call_go_api("Stop/All"), and return its JSON."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{BASE_URL}/{path}", params={"key": API_KEY})
            data = response.json()
    except httpx.HTTPError as error:                                                                                                                  
        # Don't include str(error): it contains the request URL, and so the API key.
        raise HTTPException(502, f"Could not reach Metrolinx: {type(error).__name__}")
    except ValueError:
        raise HTTPException(502, "Metrolinx returned a response that wasn't JSON")

    # Most endpoints report their status in a "Metadata" block. GTFS feeds don't have one.
    metadata = data.get("Metadata", {})
    error_code = metadata.get("ErrorCode", "")
    if response.status_code >= 400:
        raise HTTPException(response.status_code, metadata.get("ErrorMessage", "Request failed"))
    if error_code.isdigit() and int(error_code) >= 400:
        raise HTTPException(int(error_code), metadata.get("ErrorMessage", "Request failed"))

    return data


@app.get("/service-alerts", summary="Current service alerts")
async def service_alerts():
    return await call_go_api("ServiceUpdate/ServiceAlert/All")


@app.get("/exceptions", summary="Schedule exceptions, including cancelled trips and stops")
async def exceptions():
    # Not every trip here is cancelled: check each trip's IsCancelled field.
    return await call_go_api("ServiceUpdate/Exceptions/All")


@app.get("/trains", summary="All trains currently in service")
async def trains():
    return await call_go_api("ServiceataGlance/Trains/All")


@app.get("/stops/{stop_code}/next-service", summary="Upcoming departures for a stop, e.g. UN")
async def next_service(stop_code: str):
    return await call_go_api(f"Stop/NextService/{stop_code}")


@app.get("/raw/{path:path}", summary="Call any endpoint, e.g. Stop/Details/UN")
async def raw(path: str):
    return await call_go_api(path)


async def main():
    output = await call_go_api("trains")
    print(output)

if __name__ == "__main__":
    asyncio.run(main())