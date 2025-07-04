# test_hierarchical.py
import asyncio
from improved_analyzer import analyze_hierarchically

async def main():
    await analyze_hierarchically("https://example.com")

if __name__ == "__main__":
    asyncio.run(main())