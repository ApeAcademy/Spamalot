from typing import Set
from ape import project, chain
from ape.logging import logger
from silverback import SilverbackApp
from taskiq import Context, TaskiqDepends

# Constants
BLOCK_INTERVAL = 100  # Adjust this to the desired block interval for NFT minting

# Data Structures
tracked_addresses: Set[str] = set()

# NFT Contract
NFT_CONTRACT = project.erc721  # Replace this with the correct path to your NFT contract

# App Initialization
app = SilverbackApp()

@app.on_startup()
def initialize(state):
    """
    Startup function to deploy the NFT contract and initialize the state.
    """
    logger.info("Deploying NFT contract")
    nft_contract = NFT_CONTRACT.deploy(sender=app.signer)  # Ensure you have correct deploy method in your contract
    state.nft_contract = nft_contract
    state.tracked_addresses = tracked_addresses

@app.on_(chain.blocks)
async def track_active_addresses(block, context: Context = TaskiqDepends()):
    """
    Handler that tracks active addresses from transactions in each block.
    """
    if block.number % BLOCK_INTERVAL == 0:
        context.state.tracked_addresses.clear()  # Reset the set every `n` blocks

    # Track active addresses
    transactions = block.transactions
    for tx in transactions:
        context.state.tracked_addresses.add(tx.sender)

@app.on_(chain.blocks)
async def mint_and_distribute_nfts(block, context: Context = TaskiqDepends()):
    """
    Handler that mints and distributes NFTs to active addresses every `n` blocks.
    """
    if block.number % BLOCK_INTERVAL == 0 and context.state.tracked_addresses:
        logger.info("Minting and distributing NFTs to active addresses")
        for address in context.state.tracked_addresses:
            try:
                context.state.nft_contract.mint(address, sender=app.signer)  # Adjust based on your contract's API
                logger.info(f"NFT minted and sent to {address}")
            except Exception as e:
                logger.error(f"Error minting NFT for {address}: {e}")

# Run the application
if __name__ == "__main__":
    app.run()
