
from hyperliquid.info import Info
from hyperliquid.utils import constants

def test_l2():
    info = Info(base_url=constants.MAINNET_API_URL)
    snapshot = info.l2_snapshot("BTC")
    
    # Structure is likely {'levels': [[px, sz, num], ...]} 
    # OR {'bids': [], 'asks': []}
    
    print("Levels type:", type(snapshot['levels']))
    print("Levels len:", len(snapshot['levels']))
    if len(snapshot['levels']) > 0:
        print("First Item type:", type(snapshot['levels'][0]))
        print("First Item sample:", snapshot['levels'][0][:2]) # Print first 2 bids

if __name__ == "__main__":
    test_l2()
