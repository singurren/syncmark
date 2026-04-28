import numpy as np
import torch
import json
import hashlib
from tqdm import tqdm
import re
import os
import ftfy
from datasets import load_dataset
from transformers import AutoTokenizer
import random

seed = int(os.environ.get('GLOBAL_SEED', 42))
random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(seed)

def process_text(text, prompt_len):
    truncated_text = ' '.join(text.split()[:prompt_len])
    if not any(punctuation in truncated_text for punctuation in '.!?'):
        return None
    return max((truncated_text.rsplit(punct, 1)[0] + punct for punct in '.!?' if punct in truncated_text), key=len)

def load_data(dataset_name, prompt_len=100, num_test=10000, ds_start_point=0, sliding_prompt=0, model_name=None):
    if dataset_name.lower() == 'c4':
        # Reduced stream size for speed if needed, but keep original logic
        dataset = load_dataset("allenai/c4", "realnewslike", split="validation", streaming=True, trust_remote_code=True).shuffle(seed=42)
        ds_iterator = iter(dataset)
        
        t = 0
        prompts = []
        prompt_idx = []
        prompt_cnt = -1
        human_written = []
        true_num_test = 0
        while t < num_test:
            try:
                if prompt_cnt < ds_start_point:
                    next(ds_iterator)
                    prompt_cnt += 1
                else:
                    example = next(ds_iterator)
                    prompt_cnt += 1
                    text = process_text(example['text'], prompt_len)
                    if text is None: continue
                    prompts.append(text)
                    prompt_idx.append(prompt_cnt)
                    true_num_test += 1
                    human_written.append(ftfy.fix_text(example['text'][len(text):]))
                    t += 1
            except StopIteration:
                break
    elif dataset_name.lower() == 'vocab':
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        vocab = tokenizer.get_vocab()
        prompts = list(vocab.keys()) 
        prompt_idx = [vocab[key] for key in prompts]
        human_written = []
        true_num_test = len(prompts)
    return prompt_idx, prompts, human_written, true_num_test

def process_valid_text(gen_text):
    cleaned_texts = []
    for text in gen_text:
        cleaned_text = re.sub(r'<pad>', '', text)
        cleaned_text = re.sub(r'<\|end_of_text\|>', '', cleaned_text)
        cleaned_text = re.sub(r'<\|endoftext\|>', '', cleaned_text)
        cleaned_texts.append(ftfy.fix_text(cleaned_text))
    return cleaned_texts        

def record_data(prompts, tokenizer, gen_token, idx_list, save_dir, params, bits=None, output_text=False, num_return_sequences=1):
    if output_text:
        valid_text = gen_token
    else:
        gen_text = tokenizer.batch_decode(gen_token, skip_special_tokens=True)
        if num_return_sequences > 1:
            valid_text = [gen_text[i:i + num_return_sequences] for i in range(0, len(gen_text), num_return_sequences)]
        else:
            valid_text = process_valid_text(gen_text)

    jsonl_data = []
    # [DEBUG] Print if bits are being saved
    if bits:
        print(f"[DEBUG utils.py] Saving bits to jsonl: {bits[:10]}... (Len: {len(bits)})")
    else:
        print(f"[DEBUG utils.py] WARNING: bits is None or empty!")

    for i, (prompt, text) in enumerate(zip(prompts, valid_text)):
        # Handle idx_list carefully to avoid IndexError
        pid = idx_list[i] if i < len(idx_list) else -1
        
        item = {
            "prompt_idx": pid,
            "prompt": prompt,
            "generation_text": text
        }
        # [FIX] Ensure bits is string and saved if present
        if bits is not None and len(str(bits)) > 0:
            item["bits"] = str(bits)
            
        jsonl_data.append(item)
    
    content_path = os.path.join(save_dir, "generation_text.jsonl")
    with open(content_path, 'a', encoding='utf-8') as f:
        for item in jsonl_data:
            json.dump(item, f, ensure_ascii=False)
            f.write('\n')
    
    params_path = os.path.join(save_dir, "generation_params.json")
    if not os.path.exists(params_path) or os.path.getsize(params_path) == 0:
        with open(params_path, 'w', encoding='utf-8') as f:
            json.dump(params, f, ensure_ascii=False, indent=4)

def read_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f: return json.load(f)
    except:
        with open(file_path, 'r', encoding='utf-8-sig') as f: return json.load(f)

def read_jsonl_file(file_path):
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try: data.append(json.loads(line.strip()))
            except: pass
    return data

def prf(seed: torch.LongTensor, secret_key: int):
    if seed.dim() == 1:
        seed_str = ''.join(map(str, seed.tolist())) + str(secret_key)
        hash_digest = hashlib.sha256(seed_str.encode()).hexdigest()
        return int(hash_digest, 16) % 2**32
    else:
        result = []
        for row in seed:
            seed_str = ''.join(map(str, row.tolist())) + str(secret_key)
            hash_digest = hashlib.sha256(seed_str.encode()).hexdigest()
            result.append(int(hash_digest, 16) % 2**32) 
    return result