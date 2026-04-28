import argparse
from tqdm import tqdm
import torch
import random
from transformers import AutoModelForCausalLM, AutoTokenizer
import pandas as pd
import os
import numpy as np
from random import randint
try:
    from .utils import record_data, load_data
    from .WatermarkBimark import WatermarkBimark
except ImportError:
    from utils import record_data, load_data
    from WatermarkBimark import WatermarkBimark
import time
from datetime import datetime
import json
from reedsolo import RSCodec, ReedSolomonError
from syncmark.framing import build_layout

def hamming74_encode_block(nibble):
    d1 = (nibble >> 3) & 1
    d2 = (nibble >> 2) & 1
    d3 = (nibble >> 1) & 1
    d4 = (nibble >> 0) & 1
    p1 = d1 ^ d2 ^ d4
    p2 = d1 ^ d3 ^ d4
    p3 = d2 ^ d3 ^ d4
    return (d1<<6)|(d2<<5)|(d3<<4)|(d4<<3)|(p1<<2)|(p2<<1)|(p3)

def hamming74_encode_bits(bitstring):
    if len(bitstring) % 4 != 0:
        pad = 4 - (len(bitstring) % 4)
        bitstring += "0" * pad
    encoded_res = ""
    for i in range(0, len(bitstring), 4):
        chunk = bitstring[i:i+4]
        val = int(chunk, 2)
        enc_val = hamming74_encode_block(val)
        encoded_res += f"{enc_val:07b}"
    return encoded_res

def build_syncmark_schedule(message_bits, text_length, anchor_len, key):
    layout = build_layout([int(bit) for bit in message_bits], text_length=text_length, anchor_len=anchor_len, key=key)
    return ''.join(str(slot.expected_bit) for slot in layout)

seed = int(os.environ.get('GLOBAL_SEED', 42))
random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(seed)

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

def save_human_written_as_json(prompt_idx, prompts, human_written, save_dir):
    json_data = []
    for idx, prompt, completion in zip(prompt_idx, prompts, human_written):
        json_data.append({
            "prompt_idx": idx,
            "prompt": prompt,
            "human_completion": completion
        })
    with open(os.path.join(save_dir, "human_written.jsonl"), 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)

def create_save_dir(args, method, time_str):
    save_dir = f"./output_dump/{method}_{args.dataset.replace('/','_')}_{args.model_name.replace('/','-')}_"
    save_dir = save_dir + time_str
    os.makedirs(save_dir, exist_ok=True)
    return save_dir

def main(args):
    print(f"[DEBUG] Script Start. Method: {args.method}, ECC: {args.ecc_method}")
    begin = time.time()
    now = datetime.now()
    time_str = now.strftime("%Y-%m-%d %H:%M:%S").replace(' ','_').replace(":","-")
    save_dir = create_save_dir(args, args.method,  time_str)
    
    model_dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    model_kwargs = {"torch_dtype": model_dtype}
    if torch.cuda.is_available():
        model_kwargs["device_map"] = "auto"
    model = AutoModelForCausalLM.from_pretrained(args.model_name, **model_kwargs)
    if not torch.cuda.is_available():
        model = model.to(device)
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = 'left'
    model.eval()

    prob_delta = args.prob_delta
    prompt_idx, prompts, human_written, num_test = load_data(args.dataset, args.prompt_len, args.num_test)
    
    # 确保 idx 列表长度与 prompts 一致
    prompt_idx = prompt_idx[:num_test]
    prompts = prompts[:num_test]
    human_written = human_written[:num_test]
    
    with open(os.path.join(save_dir, "prompt_idx.txt"), "w") as f:
        for idx in prompt_idx: f.write(str(idx)+'\n')
    save_human_written_as_json(prompt_idx, prompts, human_written, save_dir)

    batch_size = args.batch_size
    n_batches = int(np.ceil(num_test / batch_size))
    pbar = tqdm(total=n_batches)
    
    for batch in range(n_batches):
        start_idx = batch * batch_size
        end_idx = min(num_test, (batch + 1) * batch_size)
        batch_prompts = prompts[start_idx:end_idx]
        
        inputs = tokenizer(batch_prompts, padding=True, return_tensors="pt", truncation=True)
        input_ids = inputs["input_ids"].to(model.device)
        attention_mask = inputs["attention_mask"].to(model.device)
        prompt_tokens_len = (input_ids).size(-1)
        
        encoded_bits = None
        original_bits = ""
        
        if args.method.lower() == 'bimark':
            original_bits = args.message
            if not original_bits:
                print("[WARNING] No message provided! Using default '0'*16")
                original_bits = "0" * 16 
                
            encoded_bits = original_bits
            schedule_bits = None
            schedule_mode = 'random_bit_index'
            ecc_type = args.ecc_method.lower()
            
            try:
                if ecc_type == 'reedsolomon':
                    pad_len = (8 - len(original_bits) % 8) % 8
                    bits_padded = original_bits + '0' * pad_len
                    byte_arr = bytearray()
                    for i in range(0, len(bits_padded), 8):
                        byte_arr.append(int(bits_padded[i:i+8], 2))
                    rsc = RSCodec(args.ecc_strength) 
                    encoded_bytes = rsc.encode(byte_arr)
                    encoded_bits = ""
                    for b in encoded_bytes:
                        encoded_bits += f"{b:08b}"
                elif ecc_type == 'hamming74':
                    encoded_bits = hamming74_encode_bits(original_bits)
            except Exception as e:
                print(f"[ERROR] ECC Encoding failed: {e}. Fallback to original bits.")
                encoded_bits = original_bits

            if args.syncmark_outer:
                if ecc_type != 'none':
                    raise ValueError("syncmark_outer currently expects --ecc_method none so the payload budget is controlled by SyncMark framing.")
                schedule_bits = build_syncmark_schedule(
                    original_bits,
                    text_length=args.max_new_tokens,
                    anchor_len=args.syncmark_anchor_len,
                    key=args.syncmark_key,
                )
                encoded_bits = schedule_bits
                schedule_mode = 'position_schedule'
            
            print(f"Method: {ecc_type}, Msg: {original_bits} ({len(original_bits)}), Encoded: {len(encoded_bits)}")

            watermark_processor = WatermarkBimark(
                tokenizer=tokenizer, vocab_size=model.config.vocab_size, device=device, 
                top_k=args.top_k, partition_seeds=args.partition_seeds, 
                c_key=args.c_key, bit_idx_key=args.bit_idx_key, 
                delta=prob_delta, window_size=args.window_size, bits=encoded_bits,
                schedule_mode=schedule_mode, schedule_bits=schedule_bits
            )
            gen_args = {'logits_processor': [watermark_processor], 'max_new_tokens': args.max_new_tokens,
                        'temperature': args.temperature, 'attention_mask': attention_mask, 'do_sample': args.do_sample, 'top_k': args.top_k}
        else:
            gen_args = {'max_new_tokens': args.max_new_tokens, 'attention_mask': attention_mask, 
                        'temperature': args.temperature, 'do_sample': args.do_sample, 'top_k': args.top_k}

        idx_list_batch = prompt_idx[start_idx:end_idx]

        with torch.inference_mode():
            output_tokens = model.generate(input_ids, **gen_args)

        # [FIXED] Added c_key and bit_idx_key which caused KeyError in detection
        params_record = {
            "method": args.method,
            "model_name": args.model_name,
            "vocab_size": model.config.vocab_size,
            "original_message": original_bits,
            "encoded_message": encoded_bits if encoded_bits else "",
            "ecc_method": args.ecc_method,
            "ecc_strength": args.ecc_strength,
            "syncmark_outer": args.syncmark_outer,
            "syncmark_anchor_len": args.syncmark_anchor_len,
            "syncmark_key": args.syncmark_key,
            "schedule_mode": schedule_mode if args.method.lower() == 'bimark' else "",
            "schedule_bits": schedule_bits if args.method.lower() == 'bimark' and schedule_bits else "",
            "prob_delta": prob_delta,
            "partition_seeds": args.partition_seeds,
            "window_size": args.window_size,
            "c_key": args.c_key,                # [NEW] Added
            "bit_idx_key": args.bit_idx_key,    # [NEW] Added
            "time_stamp": time_str
        }
        
        bits_arg = encoded_bits if args.method=='bimark' else None
        print(f"[DEBUG] Calling record_data with bits={'Yes' if bits_arg else 'No'}")
        record_data(batch_prompts, tokenizer, output_tokens[:,prompt_tokens_len:].tolist(), idx_list_batch, save_dir, params_record, bits=bits_arg)
        pbar.update(1)

    append_runtime(save_dir, time.time() - begin)
    print(f"AUTOMATION_OUTPUT_DIR:{os.path.basename(save_dir)}")

def append_runtime(save_dir, runtime):
    try:
        p = os.path.join(save_dir, "generation_params.json")
        with open(p, 'r') as f: d = json.load(f)
        d['runtime'] = runtime
        with open(p, 'w') as f: json.dump(d, f)
    except: pass

if __name__ == "__main__":
    def list_of_floats(arg): return list(map(float, arg.split(',')))
    def list_of_ints(arg): return list(map(int, arg.split(',')))

    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", type=str, default="meta-llama/Meta-Llama-3.1-8B")
    parser.add_argument("--method", type=str, default='bimark')
    parser.add_argument("--prob_delta", type=list_of_floats, default="1.0")
    parser.add_argument("--partition_seeds", type=list_of_ints, default=[i for i in range(10)])
    parser.add_argument("--c_key", type=int, default=8214793)
    parser.add_argument("--bit_idx_key", type=int, default=283519)
    parser.add_argument("--dataset", type=str, default="c4")
    parser.add_argument("--max_new_tokens", type=int, default=350)
    parser.add_argument("--prompt_len", type=int, default=100)
    parser.add_argument("--num_test", type=int, default=100)
    parser.add_argument("--window_size", type=int, default=2)
    parser.add_argument("--message", type=str, default="0"*16)
    parser.add_argument("--random_message", action='store_true')
    parser.add_argument("--batch_size", type=int, default=50)
    parser.add_argument("--top_k", type=int, default=50)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--do_sample", action='store_true')
    parser.add_argument("--ecc_method", type=str, default="none")
    parser.add_argument("--ecc_strength", type=int, default=0)
    parser.add_argument("--syncmark_outer", action="store_true")
    parser.add_argument("--syncmark_anchor_len", type=int, default=6)
    parser.add_argument("--syncmark_key", type=str, default="syncmark-bimark-real")
    args = parser.parse_args()
    main(args)
