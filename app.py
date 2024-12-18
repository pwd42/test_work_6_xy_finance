import asyncio
import logging

from client import Client
from config import CHAIN_ID_BY_NAME
from xy_finance import XyFinance

# Настройка логгера
def init_logger():
    logging.basicConfig(filename='myapp.log',level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    logger = logging.getLogger(__name__)

    return logger

async def print_available_chains(logger):
    xy_finance_without_client = XyFinance(logger=logger)
    chains_id_by_name_from_xy_finance = await xy_finance_without_client.get_supported_chains()
    print("Доступные сети на платформе XY Finance:\n")
    for chain in chains_id_by_name_from_xy_finance:
        print(f"{chain}")
    print("\n")

# указание пользователем сети блокчейна
async def init_chain_by_input(logger, is_input = True):
    xy_finance_without_client = XyFinance(logger=logger)
    chains_id_by_name_from_xy_finance = await xy_finance_without_client.get_supported_chains()
    while True:
        if is_input:
            chain_id = input("Enter available INPUT chainId for bridge: ")
        else:
            chain_id = input("Enter available OUTPUT chainId for bridge: ")

        try:
            chain_id = int(chain_id)

            for chain in chains_id_by_name_from_xy_finance:
                if chain_id == chain["chainId"]:
                    logger.info(f"blockchain {chain_id} is correctly!")
                    return chain_id

            print("Blockchain not available! Please try again!\n")
            logger.info(f"blockchain {chain_id} not available!")

        except ValueError:
            print("Blockchain not correctly! Please try again!\n")
            logger.warning(f"blockchain {chain_id} not correctly!")


# указание пользователем приватного ключа
def init_pk_by_input(logger, chain_name_code):
    while True:
        pk = input("Enter private key: ")
        try:
            client = Client(pk, chain_name_code)
            if client.validate_address() and (len(pk) == 66 or len(pk) == 64):
                logger.info("Private  key correctly")
                return pk
            else:
                print("Private key not correctly!")
                logger.warning(f"input private key {pk} not correctly!")
        except Exception as exc:
            print("Private key not correctly!")
            logger.warning(exc)

# указание пользователем кол-ва нативного токена для обмена
async def init_amount_native_token_for_swap_by_input(client: Client, logger):
    while True:
        try:
            amount_native_token_for_swap = float(input("\nEnter value of native token for swap in ETH (format example-\"0.0001\") : "))
            amount_native_token_for_swap_in_wei = client.to_wei_custom(amount_native_token_for_swap)
            if await check_balance_for_bridge(client, logger, amount_native_token_for_swap_in_wei):
                logger.info(f"check_balance_for_swap_by_amount for {amount_native_token_for_swap} is True")
                return amount_native_token_for_swap_in_wei
            else:
                print("\nNot enough balance for this amount! Please change amount!\n")
                logger.warning("Balance not enough for input amount nft!")
        except ValueError:
            print("Amount not number! Please try again!\n")
            logger.warning("input amount nft not correctly!")

# проверка баланса на возможность транзакции с учетом указанного  пользователем кол-ва токена
async def check_balance_for_bridge(client, logger, amount_native_token_for_swap_in_wei):

    gas_price_wei = await client.w3.eth.gas_price
    logger.info(f"gas_estimate: {gas_price_wei} WEI")
    full_estimate_cost_swap = gas_price_wei + amount_native_token_for_swap_in_wei
    logger.info(f"client balance: {await client.get_balance()} WEI")

    if await client.get_balance() > full_estimate_cost_swap:
        return True

    return False

async def main():
    logger = init_logger()
    # Вывод доступных сетей
    await print_available_chains(logger)

# ввод пользователем сети ввода и сети вывода eth через мост
    chain_id_input = 0
    chain_id_output = 0
    while chain_id_input == chain_id_output:
        chain_id_input = await init_chain_by_input(logger, is_input=True)
        chain_id_output = await init_chain_by_input(logger, is_input=False)
        if chain_id_input == chain_id_output:
            print("INPUT and OUTPUT chain`s must be different!")

    # определение name_code сети по Chain_id
    chain_name_code_for_client = None
    for k, v in CHAIN_ID_BY_NAME.items():
        if v == chain_id_input:
            chain_name_code_for_client = k

    # ввод пользователем приватного ключа
    pk = init_pk_by_input(logger, chain_name_code_for_client)

    # создание клиента и экземляра XY Finance
    client = Client(pk, chain_name_code_for_client, logger)
    xy_finance = XyFinance(client)

    # ввод кол-ва  нативного токена для моста
    amount_for_swap_in_wei = await init_amount_native_token_for_swap_by_input(client, logger)

    # выполнение транзакции моста
    await  xy_finance.execute_bridge(client, chain_id_input, chain_id_output, amount_for_swap_in_wei)



if __name__ == "__main__":
    asyncio.run(main())
