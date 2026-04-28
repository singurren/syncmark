import pandas as pd
import os
import argparse
import numpy as np

def find_nearest_hit_rate(df, length):
    """
    在DataFrame中找到最接近指定 'length' 的 'hit_rate'。
    """
    if 'length' not in df.columns or 'hit_rate' not in df.columns:
        print(f"  [Error] CSV中缺少 'length' 或 'hit_rate' 列。")
        return None
        
    # 找到 'length' 列中最接近 'length' 参数的值
    nearest_length = df.iloc[(df['length'] - length).abs().argsort()[:1]]
    
    if nearest_length.empty:
        return None
        
    return nearest_length['hit_rate'].values[0]

def main(data_dir):
    """
    主函数，用于加载数据、计算并打印总结报告。
    """
    print(f"--- 正在分析复刻实验结果 ---")
    print(f"目标目录: {data_dir}\n")

    # --- 1. 分析 Hit Rate (Message Extraction Rate) ---
    print("--- 1. 消息提取率 (Hit Rate) ---")
    
    hit_rate_csv = os.path.join(data_dir, "detect_result_wm_dp_0_0.csv")
    
    if not os.path.exists(hit_rate_csv):
        print(f"[错误] 未找到Hit Rate文件: {hit_rate_csv}")
        print("请确保你运行了 'detect_generation_text_dump.py' 且 --lex_diversity 0 --order_diversity 0\n")
        
    else:
        try:
            df_hr = pd.read_csv(hit_rate_csv)
            
            # 论文中用于对比的文本长度
            target_lengths = [50, 100, 200, 300]
            
            print(f"对比论文 Table 2 (8-bit 'Rate'):")
            for length in target_lengths:
                rate = find_nearest_hit_rate(df_hr, length)
                if rate is not None:
                    print(f"  Token 长度 ~{length}: 你的 Hit Rate = {rate*100:.2f}%")
            
            # 计算 CSV 文件中所有 Hit Rate 的总体平均值
            # 过滤掉飙升到 1.0 BER (0% Hit Rate) 的异常值，只看信号稳定区
            stable_rates = df_hr[df_hr['hit_rate'] > 0.01]['hit_rate']
            if not stable_rates.empty:
                print(f"\n  稳定信号区 (Hit Rate > 1%) 的平均值: {stable_rates.mean()*100:.2f}%")
            
        except Exception as e:
            print(f"[错误] 读取或处理 {hit_rate_csv} 时出错: {e}")

    # --- 2. 分析 Perplexity (PPL) ---
    print("\n--- 2. 困惑度 (Perplexity) ---")
    
    ppl_csv = os.path.join(data_dir, "ppl_result_300_gemma.csv")
    
    if not os.path.exists(ppl_csv):
        print(f"[错误] 未找到Perplexity文件: {ppl_csv}")
        print("请确保你运行了 'detect_generation_text_dump.py' 且带有 --perplexity 标志\n")
    else:
        try:
            df_ppl = pd.read_csv(ppl_csv)
            
            if 'bimark_ppl' in df_ppl.columns:
                avg_ppl = df_ppl['bimark_ppl'].mean()
                print(f"对比论文 Table 2 (8-bit 'PPL'):")
                print(f"  你的平均 PPL = {avg_ppl:.2f}")
                print(f"  (论文 PPL 范围: 5.78 - 8.5)")
            else:
                print(f"  [错误] CSV中缺少 'bimark_ppl' 列。")
                
        except Exception as e:
            print(f"[错误] 读取或处理 {ppl_csv} 时出错: {e}")

    print("\n--- 分析完成 ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="总结 BiMark 复刻实验的结果。")
    parser.add_argument("--data_dir", 
                        type=str, 
                        required=True, 
                        help="包含 'detect_...csv' 和 'ppl_...csv' 文件的目录名。")
    
    args = parser.parse_args()
    main(args.data_dir)