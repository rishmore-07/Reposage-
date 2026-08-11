import httpx
import asyncio
from app.modules.github.schemas import GitHubRepository

async def main():
    resp = httpx.get('https://api.github.com/users/rishmore-07/repos')
    data = resp.json()
    errors = 0
    for repo in data:
        try:
            GitHubRepository.model_validate(repo)
        except Exception as e:
            print(f"Failed on repo {repo.get('name')}: {e}")
            errors += 1
    print(f"Total errors: {errors}")

if __name__ == "__main__":
    asyncio.run(main())
