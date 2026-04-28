# Experimental plan

## 1. Goal

Test whether a synchronization-aware outer layer improves exact multi-bit recovery for short, edited LLM text without unacceptable quality degradation.

## 2. Main comparisons

### 2.1 Methods

Required baselines:

1. **BiMark** (your reproduced baseline from 9991)
2. **BiMark + naive ECC** (to connect directly to your negative result)
3. **MajorMark**
4. **DERMARK**
5. **MirrorMark**
6. **XMark**
7. **Proposed: SyncMark outer layer + reference inner marker**
8. **Proposed: SyncMark outer layer + BiMark inner layer**

If time is limited, the minimum publishable comparison set is:

- BiMark
- BiMark + naive ECC
- XMark
- SyncMark + BiMark

## 3. Data / generation tasks

Use three regimes so the paper is not overfit to one style of text.

### Regime A: news-like continuation

- Dataset: C4 RealNewsLike or another news/web continuation prompt set.
- Purpose: open-domain text with medium entropy.

### Regime B: instruction-following short responses

- Dataset: Alpaca / UltraChat-style prompts or a small curated instruction set.
- Purpose: realistic assistant outputs in the 100-250 token range.

### Regime C: low-entropy stress test

- Dataset: code prompts (MBPP/HumanEval-style) or factual QA prompts.
- Purpose: measure failure in difficult low-entropy cases where watermark capacity is limited.

## 4. Models

Primary model family:

- Llama-3.1-8B-Instruct or comparable open autoregressive model.

Optional second model for cross-model robustness:

- Mistral-7B-Instruct or Qwen2.5-7B-Instruct.

Quality scorer:

- Perplexity under a larger open model when feasible.
- Optional judge-model evaluation for fluency/meaning preservation.

## 5. Main evaluation settings

### Message lengths

- 8 bits
- 16 bits
- 32 bits

### Output lengths

- 100 tokens
- 150 tokens
- 200 tokens
- 300 tokens

### Random seeds

- At least 3 generation seeds per prompt
- At least 500 prompts total for the final main table if compute permits

## 6. Metrics

### Primary metrics

1. **Bit accuracy**
2. **Exact message recovery**
3. **CRC pass rate / valid decode rate**

### Secondary watermark metrics

4. **TPR@FPR** if a detection threshold is used
5. **Alignment recovery rate** for SyncMark-only ablations

### Quality metrics

6. **PPL**
7. **Length-normalized KL or other distortion proxy** if available
8. **Task output quality** (optional judge or task-specific metric)

## 7. Attack suite

### Attack group 1: token-level edits

- random token deletion
- random token insertion
- random token substitution

### Attack group 2: paraphrase edits

- sentence paraphrasing with a dedicated model or a strong LLM rewrite prompt
- low/medium/high paraphrase intensity settings

### Attack group 3: character-level perturbations

- adjacent swap
- single-character deletion
- homoglyph substitution
- unicode perturbation
- compound mixed char attack

This group must be in the main paper, not just the appendix.

## 8. Fairness constraints

A comparison is valid only if the following are controlled:

1. Same message length
2. Same output length budget
3. Comparable text quality or distortion budget
4. Same attack strength setting
5. Same decoding information assumptions (e.g. model-access vs model-free detector)

## 9. Key ablations for SyncMark

### A. Framing ablations

- anchor length: 4 / 6 / 8 / 10
- repeated anchor vs cycle-unique anchors
- checksum on/off

### B. Alignment ablations

- no alignment (absolute position decode)
- simple anchor matching only
- full dynamic-programming alignment

### C. Inner-layer ablations

- reference simple partition-bias inner marker
- BiMark inner layer
- optional prefix-based vs position-based partition mode

### D. Budget ablations

- same output length, different message length
- same message length, different output length

## 10. Concrete experiment sequence

### Experiment 0: synthetic validation

Run the simulator in this package and verify:
- SyncMark > repetition baseline under IDS edits
- SyncMark > Hamming baseline under IDS edits

### Experiment 1: reproduce your 9991 baseline cleanly

- Re-run BiMark on short texts: 100 / 150 / 200 / 300 tokens
- Confirm current exact recovery and quality

### Experiment 2: connect to the old negative result

- Re-run BiMark + naive ECC under the exact same short-text regime
- Include one figure explaining redundancy dilution

### Experiment 3: new method on token-level edits

- Compare BiMark, XMark, SyncMark+BiMark under deletion/insertion/substitution

### Experiment 4: new method on character-level attacks

- This is the most important main experiment
- Report exact recovery and bit accuracy under char-level perturbations

### Experiment 5: quality-vs-robustness trade-off

- Sweep watermark strength or comparable control parameter
- Show that SyncMark gains do not come only from stronger bias

## 11. What a strong main result would look like

A publishable main result would be something like:

- At 150-300 tokens and 16-32 bits payload,
- SyncMark + BiMark improves exact recovery by a clearly visible margin under deletion/insertion and character-level attacks,
- while keeping PPL close to BiMark and competitive with XMark.

Even if the method is not state-of-the-art on every setting, a convincing **mechanistic explanation** plus strong performance under real edit attacks can still be enough for a solid paper.
