import requests
from datetime import datetime, timezone
from eth_account import Account
from eth_account.messages import encode_defunct
import os
from dotenv import load_dotenv
from typing import Optional, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FractionAIAuth:
    BASE_URL = "https://dapp-backend-large.fractionai.xyz/api3"
    HEADERS = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://dapp.fractionai.xyz",
        "Referer": "https://dapp.fractionai.xyz/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    def __init__(self, private_key: str):
        self.private_key = private_key
        self.wallet_address = Account.from_key(private_key).address

    def fetch_nonce(self) -> Optional[str]:
        """Fetch authentication nonce with retry mechanism."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    f"{self.BASE_URL}/auth/nonce",
                    headers=self.HEADERS,
                    timeout=10
                )
                response.raise_for_status()
                return response.json().get('nonce')
            except requests.exceptions.RequestException as e:
                logger.error(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:
                    return None
                continue

    def generate_auth_payload(self, nonce: str) -> Tuple[str, str]:
        """Generate authentication message and timestamp."""
        issued_at = datetime.now(timezone.utc).isoformat()
        message = f"""dapp.fractionai.xyz wants you to sign in with your Ethereum account:
{self.wallet_address}

Sign in with your wallet to Fraction AI.

URI: https://dapp.fractionai.xyz
Version: 1
Chain ID: 11155111
Nonce: {nonce}
Issued At: {issued_at}"""
        return message, issued_at

    def sign_message(self, message: str) -> str:
        """Sign the authentication message."""
        encoded_message = encode_defunct(text=message)
        signed_message = Account.sign_message(encoded_message, self.private_key)
        return signed_message.signature.hex()

    def verify_dapp_auth(self) -> Optional[str]:
        """Complete authentication flow and return access token."""
        nonce = self.fetch_nonce()
        if not nonce:
            logger.error("Failed to fetch nonce")
            return None

        try:
            message, _ = self.generate_auth_payload(nonce)
            signature = self.sign_message(message)

            response = requests.post(
                f"{self.BASE_URL}/auth/verify",
                headers=self.HEADERS,
                json={
                    "message": message,
                    "referralCode": "D6AF1CEA",
                    "signature": signature
                },
                timeout=10
            )
            response.raise_for_status()
            return response.json().get('accessToken')

        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {e}")
            return None