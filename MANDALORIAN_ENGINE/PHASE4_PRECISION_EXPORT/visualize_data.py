#!/usr/bin/env python3
"""
Visualize Phase 4 Live Data
Create beautiful charts showing order flow, whale activity, and price movements
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os

# Set style
plt.style.use('dark_background')

def load_data():
    """Load collected data"""
    
    # Check for background monitoring data
    if os.path.exists('background_monitoring.csv'):
        df = pd.read_csv('background_monitoring.csv')
        print(f"✅ Loaded {len(df)} samples from background_monitoring.csv")
    elif os.path.exists('test_phase4_data.csv'):
        df = pd.read_csv('test_phase4_data.csv')
        print(f"✅ Loaded {len(df)} samples from test_phase4_data.csv")
    else:
        print("❌ No data files found")
        return None
    
    # Parse timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    return df

def create_visualizations(df):
    """Create comprehensive visualizations"""
    
    if df is None or len(df) == 0:
        print("No data to visualize")
        return
    
    # Create figure with subplots
    fig, axes = plt.subplots(4, 1, figsize=(16, 12))
    fig.suptitle('Phase 4 Live Market Data - Real-Time Analysis', 
                 fontsize=16, fontweight='bold', color='#00ff00')
    
    # 1. Price Chart
    ax1 = axes[0]
    ax1.plot(df['timestamp'], df['price'], 
             color='#00ff00', linewidth=2, label='BTC Price')
    ax1.fill_between(df['timestamp'], df['price'].min(), df['price'],
                     alpha=0.3, color='#00ff00')
    ax1.set_ylabel('Price ($)', fontsize=12, fontweight='bold')
    ax1.set_title('BTC Price Movement', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left')
    
    # Add price change annotation
    price_change = df['price'].iloc[-1] - df['price'].iloc[0]
    price_change_pct = (price_change / df['price'].iloc[0]) * 100
    ax1.text(0.02, 0.95, f'Change: ${price_change:+.2f} ({price_change_pct:+.3f}%)',
             transform=ax1.transAxes, fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='black', alpha=0.8))
    
    # 2. Order Flow Imbalance
    ax2 = axes[1]
    colors = ['#ff0000' if x < 0 else '#00ff00' for x in df['ob_imbalance']]
    ax2.bar(df['timestamp'], df['ob_imbalance'], color=colors, alpha=0.7)
    ax2.axhline(y=0, color='white', linestyle='--', alpha=0.5)
    ax2.axhline(y=0.5, color='#00ff00', linestyle=':', alpha=0.5, label='Bullish Threshold')
    ax2.axhline(y=-0.5, color='#ff0000', linestyle=':', alpha=0.5, label='Bearish Threshold')
    ax2.set_ylabel('Imbalance', fontsize=12, fontweight='bold')
    ax2.set_title('Order Flow Imbalance (Bullish/Bearish Pressure)', fontsize=14, fontweight='bold')
    ax2.set_ylim(-1.1, 1.1)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper left')
    
    # 3. Whale Activity
    ax3 = axes[2]
    ax3.plot(df['timestamp'], df['ob_large_bids'], 
             color='#00ff00', marker='o', linewidth=2, label='Whale Bids', markersize=8)
    ax3.plot(df['timestamp'], df['ob_large_asks'], 
             color='#ff0000', marker='s', linewidth=2, label='Whale Asks', markersize=8)
    ax3.fill_between(df['timestamp'], 0, df['ob_large_bids'],
                     alpha=0.3, color='#00ff00')
    ax3.fill_between(df['timestamp'], 0, df['ob_large_asks'],
                     alpha=0.3, color='#ff0000')
    ax3.set_ylabel('Whale Orders', fontsize=12, fontweight='bold')
    ax3.set_title('Whale Activity Detection', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc='upper left')
    
    # 4. Funding Rate
    ax4 = axes[3]
    ax4.plot(df['timestamp'], df['funding_pct'], 
             color='#ffaa00', linewidth=2, label='Funding Rate')
    ax4.fill_between(df['timestamp'], 0, df['funding_pct'],
                     alpha=0.3, color='#ffaa00')
    ax4.axhline(y=0, color='white', linestyle='--', alpha=0.5)
    if 'funding_is_extreme' in df.columns:
        extreme_points = df[df['funding_is_extreme'] == 1]
        if len(extreme_points) > 0:
            ax4.scatter(extreme_points['timestamp'], extreme_points['funding_pct'],
                       color='red', s=100, marker='X', label='Extreme', zorder=5)
    ax4.set_ylabel('Funding %', fontsize=12, fontweight='bold')
    ax4.set_title('Funding Rate (8h)', fontsize=14, fontweight='bold')
    ax4.set_xlabel('Time', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.legend(loc='upper left')
    
    # Format x-axis for all subplots
    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    
    # Save
    output_file = 'phase4_live_visualization.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='#0a0a0a')
    print(f"\n✅ Visualization saved to: {output_file}")
    
    return output_file

def print_summary(df):
    """Print data summary"""
    
    if df is None or len(df) == 0:
        return
    
    print("\n" + "="*60)
    print("📊 DATA SUMMARY")
    print("="*60)
    
    print(f"\nTime Range:")
    print(f"  Start: {df['timestamp'].iloc[0]}")
    print(f"  End:   {df['timestamp'].iloc[-1]}")
    print(f"  Duration: {(df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).total_seconds():.0f} seconds")
    
    print(f"\nPrice:")
    print(f"  Start: ${df['price'].iloc[0]:,.2f}")
    print(f"  End:   ${df['price'].iloc[-1]:,.2f}")
    print(f"  Change: ${df['price'].iloc[-1] - df['price'].iloc[0]:+.2f} ({((df['price'].iloc[-1] / df['price'].iloc[0]) - 1) * 100:+.3f}%)")
    print(f"  High:  ${df['price'].max():,.2f}")
    print(f"  Low:   ${df['price'].min():,.2f}")
    
    print(f"\nOrder Flow:")
    print(f"  Avg Imbalance: {df['ob_imbalance'].mean():+.3f}")
    print(f"  Bullish Samples: {len(df[df['ob_imbalance'] > 0.5])} ({len(df[df['ob_imbalance'] > 0.5])/len(df)*100:.1f}%)")
    print(f"  Bearish Samples: {len(df[df['ob_imbalance'] < -0.5])} ({len(df[df['ob_imbalance'] < -0.5])/len(df)*100:.1f}%)")
    
    print(f"\nWhale Activity:")
    print(f"  Total Whale Bids: {df['ob_large_bids'].sum():.0f}")
    print(f"  Total Whale Asks: {df['ob_large_asks'].sum():.0f}")
    print(f"  Samples with Whales: {len(df[(df['ob_large_bids'] > 0) | (df['ob_large_asks'] > 0)])} ({len(df[(df['ob_large_bids'] > 0) | (df['ob_large_asks'] > 0)])/len(df)*100:.1f}%)")
    
    print(f"\nFunding:")
    print(f"  Avg Rate: {df['funding_pct'].mean():.4f}%")
    print(f"  Min: {df['funding_pct'].min():.4f}%")
    print(f"  Max: {df['funding_pct'].max():.4f}%")
    
    print("="*60)

# Main
if __name__ == "__main__":
    print("="*60)
    print("🎨 Phase 4 Live Data Visualization")
    print("="*60)
    
    # Load data
    df = load_data()
    
    if df is not None:
        # Print summary
        print_summary(df)
        
        # Create visualizations
        output_file = create_visualizations(df)
        
        print(f"\n✅ Done! Open {output_file} to see the charts")
    else:
        print("\n❌ No data to visualize. Run data collection first.")
