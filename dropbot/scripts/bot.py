import asyncio
import json
import os
from pathlib import Path

from ape import chain, project
from ape.api import BlockAPI
from ape.contracts.base import ContractContainer, ContractInstance
from ape.logging import get_logger
from ethpm_types import ContractType
from silverback import SilverbackApp, SilverbackStartupState
from taskiq import Context, TaskiqDepends

# Constants
BLOCK_INTERVAL = 25  # Adjust this to the desired block interval for NFT minting
TOKEN_ID_START = int(os.environ.get("TOKEN_ID_START", 0))

# Get our own logger so we can set the level without affecting everything else
logger = get_logger("dropbot")
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# App Initialization
app = SilverbackApp()

# Load manifest to build contract to skip compilation
ERC721 = ContractContainer(
    ContractType(**json.load(open(Path(__file__).parent / ".build" / "erc721.json")))
)


@app.on_startup()
def initialize(startup_state: SilverbackStartupState, context: Context = TaskiqDepends()):
    """
    Startup function to deploy the NFT contract and initialize the state.
    """
    nft_contract = ERC721.deploy(
        sender=app.signer
    )  # Ensure you have correct deploy method in your contract
    logger.info(f"Deployed NFT contract to {nft_contract.address}")
    context.state.nft_contract = nft_contract
    context.state.tracked_addresses = set()
    context.state.next_id = TOKEN_ID_START


async def track_active_addresses(block: BlockAPI, context: Context):
    """
    Handler that tracks active addresses from transactions in each block.
    """
    # Track active addresses
    transactions = block.transactions
    for tx in transactions:
        logger.debug(f"Now tracking account {tx.sender}")
        context.state.tracked_addresses.add(tx.sender)


async def mint_and_distribute_nfts(block: BlockAPI, context: Context):
    """
    Handler that mints and distributes NFTs to active addresses every `n` blocks.
    """
    if block.number and block.number % BLOCK_INTERVAL == 0 and context.state.tracked_addresses:
        logger.debug("Minting and distributing NFTs to active addresses")
        for address in context.state.tracked_addresses:
            try:
                context.state.nft_contract.mint(
                    address, context.state.next_id, sender=app.signer
                )  # Adjust based on your contract's API
                context.state.next_id += 1
                logger.info(f"NFT minted and sent to {address}")
            except Exception as e:
                logger.error(f"Error minting NFT for {address}: {e}")

        # Clear so we aren't sending NFT to the same addresses every time
        context.state.tracked_addresses.clear()


@app.on_(chain.blocks)
async def handle_blocks(block: BlockAPI, context: Context = TaskiqDepends()):
    logger.debug(f"New block: {block.number}")
    await asyncio.gather(
        track_active_addresses(block, context), mint_and_distribute_nfts(block, context)
    )
