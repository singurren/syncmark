# Expected results and conclusion template

**Important:** these are pre-registered expectations and interpretation rules, not final empirical claims.

## 1. Expected outcomes

### Expected outcome A: naive ECC still underperforms in short texts

Under fixed short output lengths, BiMark + naive ECC is expected to improve little or even degrade exact recovery because extra redundancy reduces the number of informative votes available per encoded bit.

### Expected outcome B: synchronization-aware decoding helps most when edits create drift

SyncMark should show the clearest gains under:

- token insertion/deletion,
- mixed local edits,
- and especially character-level attacks that disturb tokenization.

### Expected outcome C: gains grow with enough text to repeat anchors at least a few times

When output length increases from 100 to 300 tokens, SyncMark exact recovery should improve because anchor evidence and payload repetition both accumulate.

### Expected outcome D: substitution-only settings will understate the benefit

If the attack is only substitution noise, standard ECC or repetition may look more competitive. The paper should therefore avoid claiming success based only on substitution or paraphrase benchmarks.

## 2. How to interpret positive results

If SyncMark + BiMark outperforms BiMark and BiMark + naive ECC under insertion/deletion/char-level attacks, the conclusion should be:

> The main bottleneck in short edited texts is synchronization loss, and robustness improves when outer redundancy is allocated to re-alignment rather than only to parity correction.

## 3. How to interpret mixed results

### Case 1: bit accuracy improves but exact recovery does not

Interpretation:
- the method is helping partially, but not enough for full attribution-level decoding,
- possible fixes: stronger inner layer, longer anchors, better alignment objective, or smaller payload.

### Case 2: gains appear only on the simple inner watermark, not on BiMark

Interpretation:
- the outer layer is not yet well matched to a realistic low-distortion inner embedder,
- the next step is to redesign the interface between inner evidence and outer decoding.

### Case 3: gains disappear under fairness-controlled quality matching

Interpretation:
- improvement may have come from stronger bias rather than better synchronization design,
- more careful quality normalization is required.

## 4. How to interpret negative results

If SyncMark fails to outperform well-tuned baselines, that is still useful.

The most likely conclusion would be:

> In the tested short-text regime, local signal strength rather than synchronization is the dominant bottleneck.

That negative result can still become a meaningful thesis contribution if it is backed by:

- a strong short-text benchmark,
- proper character-level attacks,
- and clear ablations showing where the method fails.

## 5. Draft conclusion paragraph for a future paper

> This work revisits multi-bit watermark recovery for short and post-edited LLM text through the lens of synchronization. Building on negative evidence that naive ECC can dilute finite-length watermark signals, we model post-editing as an insertion-deletion-substitution channel and propose a synchronization-aware outer framing and alignment decoder. Our results suggest that a substantial portion of recovery loss under realistic editing attacks comes from desynchronization rather than ordinary bit corruption. The proposed framing improves exact message recovery under short-text and character-level attacks while remaining compatible with existing inner watermarking schemes. These findings indicate that future multi-bit watermarking systems should allocate redundancy not only to parity correction but also to synchronization recovery.

## 6. Decision threshold for calling the thesis successful

A practical success threshold would be:

- clear gain over BiMark + naive ECC,
- clear gain under character-level attacks,
- at least one setting where SyncMark + BiMark is competitive with or better than XMark,
- no catastrophic quality regression.
