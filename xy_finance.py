from aiohttp import ClientSession


from client import Client

class XyFinance:
    def __init__(self, client : Client = None, logger = None):
        self.client = client
        self.logger = logger
        self.base_api_url = "https://aggregator-api.xy.finance/v1"

    @staticmethod
    async def make_request(
            method: str = 'GET', url: str = None, params: dict = None, headers: dict = None, json: dict = None
    ):
        async with ClientSession() as session:
            async with session.request(method=method, url=url, params=params, headers=headers, json=json) as response:
                if response.status in [200, 201]:
                    return await response.json()
                raise RuntimeError(f"Bad request to XY Finance API. Response status: {response.status} \n"
                                   f"Response full: {await response.json()}")

    async def get_supported_chains(self):
        url = f'{self.base_api_url}/supportedChains'
        response = await self.make_request(url=url)
        self.logger.info(f"Response get_supported_chains(): {response}")
        return response["supportedChains"]

    async def get_quote(self, src_chain_id, dst_chain_id, token_amount):
        url = f'{self.base_api_url}/quote'
        params = {
            'srcChainId': src_chain_id,
            'srcQuoteTokenAddress': "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
            'srcQuoteTokenAmount': token_amount,
            'dstChainId': dst_chain_id,
            'dstQuoteTokenAddress': "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
            'slippage': 1,
        }

        response = await self.make_request(url=url, params=params)
        if response.get('routes'):
            self.client.logger.info(f"successful response /supportedChains {response}")
            return response['routes'][0]
        self.client.logger.error(f"error response /supportedChains {response}")
        raise RuntimeError(f'Can not get current data from API: {response}')

    async def build_tx(self, client: Client, src_chain_id, dst_chain_id, token_amount):
        url = f'{self.base_api_url}/buildTx'
        response_get_quote = await self.get_quote(src_chain_id, dst_chain_id, token_amount)
        bridge_provider = response_get_quote['bridgeDescription']['provider']
        src_bridge_token_address = response_get_quote['bridgeDescription']['srcBridgeTokenAddress']
        dst_bridge_token_address = response_get_quote['bridgeDescription']['dstBridgeTokenAddress']

        params = {
            'srcChainId': src_chain_id,
            'srcQuoteTokenAddress': "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
            'srcQuoteTokenAmount': token_amount,
            'dstChainId': dst_chain_id,
            'dstQuoteTokenAddress': "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
            'slippage': 1,
            'receiver' : client.address,
            'bridgeProvider': bridge_provider,
            'srcBridgeTokenAddress': src_bridge_token_address,
            'dstBridgeTokenAddress': dst_bridge_token_address
        }

        response = await self.make_request(url=url, params=params)
        if response.get('success'):
            self.client.logger.info(f"successful response /buildTx {response}")
            return response['tx']
        self.client.logger.error(f"error response /buildTx {response}")
        raise RuntimeError(f'Can not get current data from API: {response}')

    async def execute_bridge(self, client: Client, src_chain_id, dst_chain_id, token_amount):
        response_build_tx = await self.build_tx(client, src_chain_id, dst_chain_id, token_amount)

        call_data = response_build_tx['data']
        to_contract_address = response_build_tx['to']
        value = response_build_tx['value']

        transaction = await self.client.prepare_tx(value=value) | {
            'data': call_data,
            'to': to_contract_address,
            'value': value
        }
        transaction['gas'] = int((await client.w3.eth.estimate_gas(transaction)) * 1.5)
        return await self.client.send_transaction(transaction)
