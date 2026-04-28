import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from matplotlib.lines import Line2D

# 设置绘图风格
plt.style.use('seaborn-v0_8-paper')
sns.set_context("paper", font_scale=1.4)
MANIFEST_FILE = "experiment_manifest_attack.json"
OUTPUT_PLOT_DIR = "analysis_plots_attack"

def load_data(manifest_path):
    if not os.path.exists(manifest_path): return []
    with open(manifest_path, 'r') as f: 
        try: data = json.load(f)
        except: return []
    
    processed = []
    for entry in data:
        dir_name = entry['directory']
        full_path = os.path.join("output_dump", dir_name)
        if not os.path.exists(full_path):
            if os.path.exists(dir_name): full_path = dir_name
            else: continue
        
        # PPL
        ppl_p = os.path.join(full_path, "ppl_result_all.csv")
        entry['ppl'] = pd.read_csv(ppl_p).iloc[:,0].mean() if os.path.exists(ppl_p) else np.nan
            
        # Detection
        atk = entry['attack_strength']
        fname = "detect_result_wm.csv" if atk == 0 else f"detect_result_wm_dp_{atk}_{atk}.csv"
        csv_path = os.path.join(full_path, fname)
        
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                if 'hit_rate' not in df.columns and 'ber' in df.columns:
                    df['hit_rate'] = 1.0 - df['ber']
                entry['detect_df'] = df
            except: entry['detect_df'] = None
        else: entry['detect_df'] = None
            
        processed.append(entry)
    return processed

# ================= 1. ECC Integrated Plots =================
def plot_ecc_integrated(data):
    """
    Plot 3 Charts (8bit, 16bit, 32bit).
    Axis: X=Text Length, Y=Extraction Rate.
    Color: Method (None=Gray, Hamming=Blue, RS=Red).
    Alpha/Style: Attack Strength (0=Solid, 60=Dotted/Light).
    """
    ecc_data = [x for x in data if x['experiment_group'] == 'ecc' and x['detect_df'] is not None]
    if not ecc_data: return

    msg_lens = sorted(list(set(x['msg_len'] for x in ecc_data)))
    target_lens = [50, 100, 200, 300, 400, 500]
    
    # Method Colors
    colors = {'none': '#7f7f7f', 'hamming74': '#1f77b4', 'reedsolomon': '#d62728'}
    # Attack Styles: Strength -> (LineStyle, Alpha)
    # 0: Solid, Dark; 60: Dotted, Light
    styles = {
        0:  ('-', 1.0, 'o'),
        20: ('--', 0.8, '^'),
        40: ('-.', 0.6, 's'),
        60: (':', 0.4, 'x')
    }

    for ml in msg_lens:
        plt.figure(figsize=(10, 7))
        subset = [x for x in ecc_data if x['msg_len'] == ml]
        
        for item in subset:
            method = item['ecc_method']
            atk = item['attack_strength']
            df = item['detect_df']
            
            # Extract data points matching target lengths
            df_filtered = df[df['length'].isin(target_lens)].sort_values('length')
            if df_filtered.empty: continue
            
            # Group by length to get mean if multiple entries exist
            df_grouped = df_filtered.groupby('length')['hit_rate'].mean().reset_index()
            
            ls, alpha, marker = styles.get(atk, ('-', 0.5, None))
            c = colors.get(method, 'black')
            
            plt.plot(df_grouped['length'], df_grouped['hit_rate'], 
                     label=None, # Legend handled manually
                     color=c, linestyle=ls, alpha=alpha, marker=marker, linewidth=2, markersize=6)

        # Custom Legend
        lines = [
            Line2D([0], [0], color=colors['none'], lw=2, label='No ECC'),
            Line2D([0], [0], color=colors['hamming74'], lw=2, label='Hamming(7,4)'),
            Line2D([0], [0], color=colors['reedsolomon'], lw=2, label='Reed-Solomon')
        ]
        # Add Attack Legend
        lines.append(Line2D([0], [0], color='black', lw=0, label=' '))
        lines.append(Line2D([0], [0], color='black', lw=0, label='Attack Strength:'))
        for atk in sorted(styles.keys()):
            ls, a, m = styles[atk]
            lines.append(Line2D([0], [0], color='black', linestyle=ls, alpha=a, marker=m, label=f'Atk {atk}'))

        plt.legend(handles=lines, loc='lower right', ncol=2, fontsize='small')
        plt.title(f"ECC Robustness: Msg Length {ml} bits")
        plt.xlabel("Text Length (Tokens)")
        plt.ylabel("Extraction Rate")
        plt.ylim(0.4, 1.02)
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.savefig(f"{OUTPUT_PLOT_DIR}/ECC_Integrated_Msg{ml}.png", bbox_inches='tight')
        plt.close()

# ================= 2. Delta Pattern Plots =================
def plot_delta_patterns(data):
    """
    Plot Rate vs Length.
    Facet by Attack Strength (0, 20, 40, 60).
    Color by Pattern.
    Separate files for each Msg Length.
    """
    d_data = [x for x in data if x['experiment_group'] == 'delta' and x['detect_df'] is not None]
    if not d_data: return
    
    msg_lens = sorted(list(set(x.get('msg_len', 16) for x in d_data))) # Default 16 if missing
    attack_levels = sorted(list(set(x['attack_strength'] for x in d_data)))
    
    # Fix Layer to 10 for Pattern Comparison (Control Variable)
    fixed_layer = 10
    
    cols = {'constant': 'gray', 'increasing': 'green', 'decreasing': 'red'}
    
    for ml in msg_lens:
        # Create a figure with subplots for each attack strength
        fig, axes = plt.subplots(1, 4, figsize=(20, 5), sharey=True)
        if len(attack_levels) != 4: axes = [axes] # Handle case if fewer levels
        
        subset_ml = [x for x in d_data if x.get('msg_len') == ml and x['layers'] == fixed_layer]
        
        for i, atk in enumerate(attack_levels):
            ax = axes[i] if len(attack_levels) > 1 else axes
            subset_atk = [x for x in subset_ml if x['attack_strength'] == atk]
            
            for item in subset_atk:
                pat = item['pattern']
                df = item['detect_df']
                # Filter and sort
                df = df[df['length'].isin([50, 100, 200, 300, 400, 500])].sort_values('length')
                df_grp = df.groupby('length')['hit_rate'].mean().reset_index()
                
                ax.plot(df_grp['length'], df_grp['hit_rate'], 
                        marker='o', color=cols.get(pat, 'k'), label=pat, lw=2)
            
            ax.set_title(f"Attack: {atk}")
            ax.set_xlabel("Text Length")
            if i == 0: ax.set_ylabel("Extraction Rate")
            ax.grid(True, linestyle='--', alpha=0.5)
            if i == 0: ax.legend() # Only legend on first
            
        plt.suptitle(f"Delta Pattern Impact (Msg {ml} bits, {fixed_layer} Layers)", y=1.05)
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_PLOT_DIR}/Delta_Pattern_Msg{ml}.png", bbox_inches='tight')
        plt.close()

# ================= 3. PPL Summary =================
def plot_ppl_summary(data):
    """
    Bar chart comparing PPL across configurations.
    """
    # 1. ECC PPL
    ecc_data = [x for x in data if x['experiment_group'] == 'ecc' and not np.isnan(x['ppl'])]
    # De-duplicate: PPL is same for all attack strengths of same config
    # Key: (ecc_method, msg_len)
    seen = set()
    ecc_unique = []
    for x in ecc_data:
        k = (x['ecc_method'], x['msg_len'])
        if k not in seen:
            seen.add(k)
            ecc_unique.append(x)
            
    # 2. Delta PPL (Fixed 10 layers)
    delta_data = [x for x in data if x['experiment_group'] == 'delta' and x['layers'] == 10 and not np.isnan(x['ppl'])]
    seen = set()
    delta_unique = []
    for x in delta_data:
        k = (x['pattern'], x.get('msg_len', 16))
        if k not in seen:
            seen.add(k)
            delta_unique.append(x)

    if not ecc_unique and not delta_unique: return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Plot ECC
    if ecc_unique:
        df_ecc = pd.DataFrame([{ 'Method': x['ecc_method'], 'Msg Len': x['msg_len'], 'PPL': x['ppl'] } for x in ecc_unique])
        sns.barplot(data=df_ecc, x='Method', y='PPL', hue='Msg Len', ax=ax1, palette='Blues')
        ax1.set_title("Text Quality (PPL) by ECC Method")
        ax1.set_ylim(bottom=df_ecc['PPL'].min()*0.9)
    
    # Plot Delta
    if delta_unique:
        df_delta = pd.DataFrame([{ 'Pattern': x['pattern'], 'Msg Len': x.get('msg_len',16), 'PPL': x['ppl'] } for x in delta_unique])
        sns.barplot(data=df_delta, x='Pattern', y='PPL', hue='Msg Len', ax=ax2, palette='Greens')
        ax2.set_title("Text Quality (PPL) by Delta Pattern (10 Layers)")
        ax2.set_ylim(bottom=df_delta['PPL'].min()*0.9)
        
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_PLOT_DIR}/PPL_Summary.png", bbox_inches='tight')
    plt.close()

def main():
    os.makedirs(OUTPUT_PLOT_DIR, exist_ok=True)
    data = load_data(MANIFEST_FILE)
    if not data: 
        print("No data found.")
        return
    
    print("Generating ECC Integrated Plots...")
    plot_ecc_integrated(data)
    
    print("Generating Delta Pattern Plots...")
    plot_delta_patterns(data)
    
    print("Generating PPL Summary...")
    plot_ppl_summary(data)
    
    print(f"Analysis complete. Plots saved to {OUTPUT_PLOT_DIR}")

if __name__ == "__main__":
    main()