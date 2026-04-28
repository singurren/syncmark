# Suggested paper outline

## Working title

**SyncMark: Synchronization-Aware Multi-bit Watermarking for Short and Edited LLM Texts**

## Abstract

One paragraph structured as:

1. short-text multi-bit watermarking matters,
2. current work still fails under realistic edits,
3. main claim: synchronization loss is a key hidden bottleneck,
4. propose outer anchor framing + alignment decoder,
5. summarize gains under short-text and char-level attacks.

## 1. Introduction

- Motivation: provenance, attribution, misuse tracing
- Why 1-bit detection is not enough
- Why short texts are the real hard regime
- Why your 9991 negative result matters
- Contributions list

## 2. Background and related work

- KGW and logits-based watermarking
- unbiased / distribution-preserving methods
- multi-bit methods: RSBH, RBC, BiMark, DERMARK, MajorMark, MirrorMark, XMark
- attacks and edit localization

## 3. Problem formulation

- define short-text multi-bit recovery
- define IDS edit channel
- define character-level tokenization drift
- explain finite-length redundancy dilution

## 4. Method

- outer framing with cycle-unique anchors
- checksum / validity mechanism
- alignment-aware decoding
- optional integration with BiMark inner layer

## 5. Experiments

- datasets, models, prompt regimes
- baselines
- attack suite
- metrics and fairness controls

## 6. Results

Main figures:

1. exact recovery vs text length
2. exact recovery under character-level attacks
3. quality-vs-robustness trade-off
4. ablation on anchor length / alignment / checksum

## 7. Analysis

- where alignment helps
- failure cases
- when local signal strength dominates instead

## 8. Conclusion

- summarize synchronization insight
- note compatibility with existing inner schemes
- discuss future work on adaptive detectors and diffusion models

## Appendix ideas

- synthetic channel analysis
- implementation details
- additional attack settings
- extra low-entropy/code results
