import aiohttp
import asyncio
import random
import logging
import traceback
from typing import Dict, List, Optional
from datetime import datetime
import os
from access_token import FractionAIAuth
import colorama
from colorama import Fore, Style
import json
from aiohttp import ClientTimeout
from asyncio import TimeoutError
from dotenv import load_dotenv


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GameSession:
    BASE_URL = "https://dapp-backend-large.fractionai.xyz/api3"
    
    def __init__(self, token: str, user_id: int):
        self.token = token
        self.user_id = user_id
        self.headers = self._generate_headers()
        self.agent_ids = [26641, 26733, 26854, 39534, 39294, 39437, 
                         79691, 79722, 79797, 79661, 79753, 79829, 
                         85172, 85203, 85248, 85128, 85153]
        self.entry_fees = [0.0001, 0.001]
        self.timeout = ClientTimeout(total=30)

    def _generate_headers(self) -> Dict:
        """Generate request headers with current token."""
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Origin": "https://dapp.fractionai.xyz",
            "Referer": "https://dapp.fractionai.xyz/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    async def refresh_token(self, private_key: str) -> None:
        """Refresh the authentication token."""
        auth = FractionAIAuth(private_key)
        new_token = auth.verify_dapp_auth()
        if new_token:
            self.token = new_token
            self.headers = self._generate_headers()
            with open("access_token.txt", "w") as file:
                file.write(new_token)
            logger.info("Token refreshed successfully")
        else:
            logger.error("Failed to refresh token")

    async def initiate_match(self, session: aiohttp.ClientSession, agent_id: int) -> Optional[Dict]:
        try:
            payload = {
                "agentId": agent_id,
                "entryFees": random.choice(self.entry_fees),
                "sessionTypeId": 1,
                "userId": self.user_id
            }
            
            async with session.post(
                f"{self.BASE_URL}/matchmaking/initiate",
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            ) as response:
                data = await response.json()
                
                if response.status == 200:
                    logger.info(f"{Fore.GREEN}Match initiated successfully with agent {agent_id}{Style.RESET_ALL}")
                    return data
                elif "error" in data:
                    if "Not found" in data["error"]:
                        logger.warning(f"{Fore.YELLOW}Agent {agent_id} in cooldown. Waiting...{Style.RESET_ALL}")
                        await asyncio.sleep(180)
                        return None
                    elif "Invalid token" in data["error"] or "Authentication token required" in data["error"]:
                        await self.refresh_token(os.getenv('PRIVATE_KEY'))
                
                logger.error(f"{Fore.RED}Error initiating match: {data}{Style.RESET_ALL}")
                await asyncio.sleep(60)
                return None

        except (TimeoutError, aiohttp.ClientError) as e:
            logger.error(f"Attempt failed: {e}")
            await asyncio.sleep(5)

    async def run(self):
        """Main execution flow with connection pooling."""
        connector = aiohttp.TCPConnector(limit=10)  # Connection pooling
        async with aiohttp.ClientSession(connector=connector) as session:
            while True:
                try:
                    tasks = [self.initiate_match(session, agent_id) 
                            for agent_id in self.agent_ids]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Process results and handle any exceptions
                    for agent_id, result in zip(self.agent_ids, results):
                        if isinstance(result, Exception):
                            logger.error(f"Error processing agent {agent_id}: {result}")
                        elif result:
                            logger.info(f"Successfully processed agent {agent_id}")
                    
                    logger.info(f"{Fore.WHITE}Completed one full cycle. Starting next...{Style.RESET_ALL}")
                    await asyncio.sleep(10)  # Prevent too frequent requests
                
                except Exception as e:
                    logger.error(f"Unhandled exception in run loop: {e}")
                    logger.error(traceback.format_exc())
                    await asyncio.sleep(60)

async def main():
    # Load configuration
    load_dotenv()
    private_key = os.getenv('PRIVATE_KEY')
    
    # Initialize colorama
    colorama.init(autoreset=True)
    
    # Read existing token or generate new one
    try:
        with open("access_token.txt", "r") as file:
            token = file.read().strip()
    except FileNotFoundError:
        auth = FractionAIAuth(private_key)
        token = auth.verify_dapp_auth()
        if token:
            with open("access_token.txt", "w") as file:
                file.write(token)
    
    if not token:
        logger.error("Failed to initialize token")
        return
    
    # Start game session
    game_session = GameSession(token=token, user_id=17267)
    await game_session.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error: {e}")
        logger.error(traceback.format_exc())