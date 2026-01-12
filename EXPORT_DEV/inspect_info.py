
from hyperliquid.info import Info
from hyperliquid.utils import constants

def inspect_info():
    info = Info(base_url=constants.MAINNET_API_URL)
    methods = [m for m in dir(info) if not m.startswith('__')]
    print("Methods in Info class:")
    for m in methods:
        print(f" - {m}")

if __name__ == "__main__":
    inspect_info()
