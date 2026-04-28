import argparse
import torch
from transformers import AutoTokenizer
import pandas as pd
import os
import numpy as np
import time
import json
import traceback
try:
    from .perplexity import LocalModel
    from .utils import read_json_file, read_jsonl_file
    from .detect_watermark_dump import WatermarkDetector
except ImportError:
    from perplexity import LocalModel
    from utils import read_json_file, read_jsonl_file
    from detect_watermark_dump import WatermarkDetector
from tqdm import tqdm
try:
    from .dipper import DipperParaphraser
except ImportError:
    from dipper import DipperParaphraser
from reedsolo import RSCodec, ReedSolomonError
import random

seed = int(os.environ.get('GLOBAL_SEED', 42))
random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(seed)

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
device = 'cuda' if torch.cuda.is_available() else 'cpu'

def hamming74_decode_block(val7):
    d1 = (val7 >> 6) & 1
    d2 = (val7 >> 5) & 1
    d3 = (val7 >> 4) & 1
    d4 = (val7 >> 3) & 1
    p1 = (val7 >> 2) & 1
    p2 = (val7 >> 1) & 1
    p3 = (val7 >> 0) & 1
    
    s1 = p1 ^ d1 ^ d2 ^ d4
    s2 = p2 ^ d1 ^ d3 ^ d4
    s3 = p3 ^ d2 ^ d3 ^ d4
    syndrome = (s1) | (s2 << 1) | (s3 << 2)
    
    if syndrome == 3: d1 ^= 1
    elif syndrome == 5: d2 ^= 1
    elif syndrome == 6: d3 ^= 1
    elif syndrome == 7: d4 ^= 1
    
    return (d1<<3)|(d2<<2)|(d3<<1)|d4

def hamming74_decode_bits(encoded_str, target_len_bits):
    decoded_bits = ""
    for i in range(0, len(encoded_str), 7):
        if i+7 > len(encoded_str): break
        chunk_str = encoded_str[i:i+7].replace('x', '0')
        try:
            val = int(chunk_str, 2)
            dec_val = hamming74_decode_block(val)
            decoded_bits += f"{dec_val:04b}"
        except:
            pass 
    return decoded_bits[:target_len_bits]

def main(args):
    print(f"DEBUG: Starting script for dir: {args.data_dir}")
    path = os.path.join("output_dump", args.data_dir)
    param_path = os.path.join(os.getcwd(), f"{path}", "generation_params.json")
    
    if not os.path.exists(param_path):
        print(f"ERROR: Params file not found at {param_path}")
        return

    params = read_json_file(param_path)
    model_name = params.get('model_name')
    
    if args.paraphrase_detect:
        content_path = os.path.join(os.getcwd(), f"{path}", f"paraphrase_text_{args.lex_diversity}_{args.order_diversity}.jsonl")
        detect_save_path = os.path.join(os.getcwd(), f"{path}", f"detect_result_wm_dp_{args.lex_diversity}_{args.order_diversity}.csv")
    else:
        content_path = os.path.join(os.getcwd(), f"{path}", "generation_text.jsonl")
        detect_save_path = os.path.join(os.getcwd(), f"{path}", "detect_result_wm.csv")

    if not os.path.exists(content_path):
        print(f"ERROR: Content file not found at {content_path}")
        return

    content = read_jsonl_file(content_path)
    print(f"DEBUG: Loaded {len(content)} items from {os.path.basename(content_path)}")
    
    tokenizer = None
    scorer = None
    dp = None
    
    if args.detect:
        print(f"DEBUG: Loading Tokenizer: {model_name}")
        tokenizer = AutoTokenizer.from_pretrained(model_name, torch_dtype=torch.bfloat16)
        tokenizer.pad_token = tokenizer.eos_token
    
    if args.perplexity:
        print("DEBUG: Loading Gemma for PPL")
        ppl_model = "google/gemma-2-9b"
        tokenizer_ppl = AutoTokenizer.from_pretrained(ppl_model, torch_dtype=torch.bfloat16)
        scorer = LocalModel(ppl_model, device)
        
    if args.paraphrase_attack:
        print("DEBUG: Loading Dipper for Attack")
        dp = DipperParaphraser(model="kalpeshk2011/dipper-paraphraser-xxl")

    # --- PPL ---
    if args.perplexity:
        ppl_list = []
        ppl_save_path = os.path.join(os.getcwd(), f"{path}", "ppl_result_all.csv")
        for item in tqdm(content, desc="Calculating PPL"):
            try:
                gen_text = item.get('generation_text', '')
                prompt = item.get('prompt', '')
                if len(gen_text) < 10: continue
                score = scorer.get_perplexity(prompt, [gen_text])
                ppl_list.extend(score)
            except Exception as e:
                print(f"Error in PPL calc: {e}")
        pd.DataFrame(ppl_list, columns=['ppl']).to_csv(ppl_save_path, index=False)
        print(f"DEBUG: PPL saved to {ppl_save_path}")

    # --- Attack ---
    if args.paraphrase_attack:
        para_save_path = os.path.join(os.getcwd(), f"{path}", f"paraphrase_text_{args.lex_diversity}_{args.order_diversity}.jsonl")
        batch_size = args.paraphrase_batch
        print(f"DEBUG: Paraphrasing to {para_save_path}")
        with open(para_save_path, 'w', encoding='utf-8') as f:
            for i in tqdm(range(0, len(content), batch_size), desc="Paraphrasing"):
                try:
                    batch = content[i:i+batch_size]
                    texts = [b.get('generation_text', '') for b in batch]
                    prompts = [b.get('prompt', '') for b in batch]
                    try:
                        outputs = dp.paraphrase_batch(texts, lex_diversity=args.lex_diversity, order_diversity=args.order_diversity, prefixes=prompts)
                    except Exception as e:
                        print(f"Dipper failed batch {i}: {e}")
                        outputs = texts # Fallback
                    
                    for item, para in zip(batch, outputs):
                        new_item = item.copy()
                        new_item['paraphrase_text'] = para
                        json.dump(new_item, f, ensure_ascii=False)
                        f.write('\n')
                except Exception as e:
                    print(f"Error in Attack loop: {e}")

    # --- Detect ---
    if args.detect:
        vocab_size = params['vocab_size']
        seeds = params.get("partition_seeds", [0])
        weights = params.get("prob_delta", [1.0])
        
        if not isinstance(weights, list): weights = [weights]
        if len(weights) == 1 and len(seeds) > 1: weights = weights * len(seeds)
        
        print("DEBUG: Initializing WatermarkDetector")
        detector = WatermarkDetector(tokenizer, vocab_size, window_size=params.get('window_size', 2), gamma=0.5)
        
        results = []
        original_msg = params.get("original_message", "")
        ecc_method = params.get("ecc_method", "none").lower()
        ecc_strength = params.get("ecc_strength", 0)
        
        # [DEBUG] Fallback keys if missing
        c_key = params.get('c_key', 8214793)
        bit_idx_key = params.get('bit_idx_key', 283519)
        
        target_lengths = [10, 25, 50, 100, 200, 300, 400, 500]
        
        print(f"DEBUG: ECC={ecc_method}, MsgLen={len(original_msg)}")
        
        success_count = 0
        skipped_count = 0
        length_fail_count = 0
        
        for item in tqdm(content, desc="Detecting"):
            try:
                text = item.get('paraphrase_text', '') if args.paraphrase_detect else item.get('generation_text', '')
                if not text: 
                    skipped_count += 1
                    continue 
                
                tokens = tokenizer.encode(text, return_tensors='pt', add_special_tokens=False)[0].to(device)
                bits_encoded = item.get('bits', '')
                
                if not bits_encoded:
                    if skipped_count < 1: print("DEBUG: Skipping item with empty bits")
                    skipped_count += 1
                    continue
                
                item_detected = False
                
                for t_len in target_lengths:
                    if len(tokens) < t_len: continue
                    
                    curr_tokens = tokens[:t_len]
                    
                    # [FIXED] Use variables with defaults
                    ret = detector.decode_bimark_multibit_watermark(
                        inputs=curr_tokens, partition_seeds=seeds, c_key=c_key, 
                        bit_idx_key=bit_idx_key, bits=bits_encoded, bits_len=len(bits_encoded), 
                        weight=weights, start=25, stride=t_len
                    )
                    
                    decoded_bits_list = ret[6]
                    
                    if not decoded_bits_list: continue
                    
                    raw_extracted_bits = decoded_bits_list[0].replace('x', '0')
                    final_extracted_msg = ""
                    
                    if ecc_method == 'reedsolomon':
                        try:
                            byte_arr = bytearray()
                            for i in range(0, len(raw_extracted_bits), 8):
                                byte_arr.append(int(raw_extracted_bits[i:i+8], 2))
                            rsc = RSCodec(ecc_strength)
                            decoded_bytes = rsc.decode(byte_arr)[0]
                            for b in decoded_bytes: final_extracted_msg += f"{b:08b}"
                            final_extracted_msg = final_extracted_msg[:len(original_msg)]
                        except:
                            final_extracted_msg = raw_extracted_bits[:len(original_msg)]
                    elif ecc_method == 'hamming74':
                        final_extracted_msg = hamming74_decode_bits(raw_extracted_bits, len(original_msg))
                    else:
                        final_extracted_msg = raw_extracted_bits[:len(original_msg)]
                    
                    hits = 0
                    match_len = min(len(original_msg), len(final_extracted_msg))
                    if match_len > 0:
                        for i in range(match_len):
                            if original_msg[i] == final_extracted_msg[i]: hits += 1
                        hit_rate = hits / len(original_msg)
                    else:
                        hit_rate = 0.0
                    
                    results.append({ "length": t_len, "hit_rate": hit_rate, "ber": 1.0 - hit_rate })
                    item_detected = True
                
                if item_detected:
                    success_count += 1
                else:
                    length_fail_count += 1
                    
            except Exception as e:
                print(f"ERROR Processing item: {e}")
                traceback.print_exc() 
                
        print(f"DEBUG: Detection finished. {success_count} items processed successfully.")
        print(f"DEBUG: {skipped_count} items skipped (empty text/bits).")
        print(f"DEBUG: {length_fail_count} items failed length check (too short).")
        
        if results:
            df = pd.DataFrame(results)
            df.to_csv(detect_save_path, index=False)
            print(f"DEBUG: Saved results to {detect_save_path}")
        else:
            print("DEBUG: No results to save!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str)
    parser.add_argument("--perplexity", action="store_true")
    parser.add_argument("--detect", action="store_true")
    parser.add_argument("--paraphrase_attack", action="store_true")
    parser.add_argument("--paraphrase_detect", action="store_true")
    parser.add_argument("--length_all", action="store_true")
    parser.add_argument("--ppl_length", type=int, default=200)
    parser.add_argument("--lex_diversity", type=int, default=0)
    parser.add_argument("--order_diversity", type=int, default=20)
    parser.add_argument("--paraphrase_batch", type=int, default=1)
    parser.add_argument("--local_model", action="store_true")
    args = parser.parse_args()
    main(args)
