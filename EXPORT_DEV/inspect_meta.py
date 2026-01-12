from hyperliquid.info import Info
from hyperliquid.utils import constants
import json

def inspect():
    info = Info(base_url=constants.MAINNET_API_URL)
    # meta_and_asset_ctxs usually has the state of all assets
    data = info.meta_and_asset_ctxs()
    
    # It returns a tuple: (meta, asset_ctxs)
    meta, asset_ctxs = data
    
    print("Meta keys:", meta.keys())
    # universe = meta['universe']
    
    # Asset Contexts usually has funding
    print("Asset Ctxs count:", len(asset_ctxs))
    if asset_ctxs:
        print("Sample Asset Ctx:", asset_ctxs[0])
        
        # Find BTC
        btc_idx = -1
        for i, u in enumerate(meta['universe']):
            if u['name'] == 'BTC':
                btc_idx = i
                break
        
        if btc_idx != -1:
            print(f"BTC found at index {btc_idx}")
            btc_ctx = asset_ctxs[btc_idx]
            print("BTC Context:", btc_ctx)
            # Check for funding
            # Usually 'funding' or 'premium'
            
if __name__ == "__main__":
    inspect()
