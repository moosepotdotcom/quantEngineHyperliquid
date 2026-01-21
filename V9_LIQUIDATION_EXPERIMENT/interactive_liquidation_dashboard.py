#!/usr/bin/env python3
"""
INTERACTIVE LIQUIDATION HEATMAP DASHBOARD
Real-time, dynamic visualization using Plotly
Integrates with existing dashboard
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime

def create_interactive_liquidation_heatmap(csv_path='liquidation_data/REAL_liquidations_continuous.csv'):
    """Create interactive Plotly heatmap"""
    
    # Load data
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Separate long and short liquidations
    long_liqs = df[df['side'] == 'A']
    short_liqs = df[df['side'] == 'B']
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('🔥 Liquidation Heatmap - Volume by Price', '⏰ Liquidation Timeline'),
        vertical_spacing=0.15,
        row_heights=[0.5, 0.5]
    )
    
    # Plot 1: Heatmap histogram
    fig.add_trace(
        go.Histogram(
            x=long_liqs['price'],
            y=long_liqs['size'],
            histfunc='sum',
            name='Long Liquidations',
            marker_color='rgba(255, 0, 0, 0.7)',
            nbinsx=50,
            hovertemplate='Price: $%{x:,.0f}<br>Volume: %{y:.2f} BTC<extra></extra>'
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Histogram(
            x=short_liqs['price'],
            y=short_liqs['size'],
            histfunc='sum',
            name='Short Liquidations',
            marker_color='rgba(0, 255, 0, 0.7)',
            nbinsx=50,
            hovertemplate='Price: $%{x:,.0f}<br>Volume: %{y:.2f} BTC<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Current price line
    current_price = df['price'].iloc[-1]
    fig.add_vline(
        x=current_price,
        line_dash="dash",
        line_color="blue",
        annotation_text=f"Current: ${current_price:,.0f}",
        row=1, col=1
    )
    
    # Plot 2: Timeline scatter
    fig.add_trace(
        go.Scatter(
            x=long_liqs['timestamp'],
            y=long_liqs['price'],
            mode='markers',
            name='Long Liquidations',
            marker=dict(
                size=long_liqs['size']*20,
                color='red',
                opacity=0.6,
                line=dict(width=1, color='darkred')
            ),
            hovertemplate='Time: %{x}<br>Price: $%{y:,.0f}<br>Size: %{marker.size:.2f} BTC<extra></extra>'
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=short_liqs['timestamp'],
            y=short_liqs['price'],
            mode='markers',
            name='Short Liquidations',
            marker=dict(
                size=short_liqs['size']*20,
                color='green',
                opacity=0.6,
                line=dict(width=1, color='darkgreen')
            ),
            hovertemplate='Time: %{x}<br>Price: $%{y:,.0f}<br>Size: %{marker.size:.2f} BTC<extra></extra>'
        ),
        row=2, col=1
    )
    
    # Update layout
    fig.update_xaxes(title_text="Price (USD)", row=1, col=1)
    fig.update_yaxes(title_text="Liquidation Volume (BTC)", row=1, col=1)
    fig.update_xaxes(title_text="Time", row=2, col=1)
    fig.update_yaxes(title_text="Price (USD)", row=2, col=1)
    
    fig.update_layout(
        title={
            'text': '🔥 Real-Time BTC Liquidation Heatmap',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': '#00ff00'}
        },
        template='plotly_dark',
        height=900,
        showlegend=True,
        hovermode='closest'
    )
    
    # Save as HTML for dashboard
    output_html = 'liquidation_data/interactive_heatmap.html'
    fig.write_html(output_html)
    
    # Also save as JSON for API integration
    output_json = 'liquidation_data/heatmap_data.json'
    with open(output_json, 'w') as f:
        json.dump({
            'current_price': float(current_price),
            'total_liquidations': len(df),
            'long_liquidations': len(long_liqs),
            'short_liquidations': len(short_liqs),
            'total_volume': float(df['size'].sum()),
            'timestamp': datetime.now().isoformat(),
            'near_liquidations': get_near_liquidations(df, current_price)
        }, f, indent=2)
    
    return output_html, output_json

def get_near_liquidations(df, current_price, proximity=0.02):
    """Get liquidations near current price"""
    near_min = current_price * (1 - proximity)
    near_max = current_price * (1 + proximity)
    near = df[(df['price'] >= near_min) & (df['price'] <= near_max)]
    
    return {
        'count': len(near),
        'volume': float(near['size'].sum()),
        'long_count': len(near[near['side'] == 'A']),
        'short_count': len(near[near['side'] == 'B']),
        'avg_price': float(near['price'].mean()) if len(near) > 0 else 0
    }

if __name__ == "__main__":
    print("🚀 Creating Interactive Liquidation Heatmap...")
    html_file, json_file = create_interactive_liquidation_heatmap()
    print(f"✅ HTML: {html_file}")
    print(f"✅ JSON: {json_file}")
    print("\\n📊 Open HTML file in browser for interactive visualization!")
