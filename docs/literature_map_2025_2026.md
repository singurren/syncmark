# Literature map for LLM watermarking (foundations -> 2026)

This reading list is optimized for your 9993 topic rather than for completeness. The goal is to quickly re-enter the field after not following it closely since late 2025.

## 1. Foundation papers you must know

| Topic | Paper | Why it matters | Link |
|---|---|---|---|
| Classical logits-based watermark | Kirchenbauer et al., **A Watermark for Large Language Models** (ICML 2023) | The KGW green-list framework is still the canonical baseline for detection-style watermarking. | https://proceedings.mlr.press/v202/kirchenbauer23a.html |
| Unbiased watermarking | Hu et al., **Unbiased Watermark for Large Language Models** (2023) | Formalizes distortion-free / unbiased watermarking, important for understanding why quality preservation matters. | https://arxiv.org/abs/2310.10669 |
| Distribution-preserving accessible watermark | Wu et al., **A Resilient and Accessible Distribution-Preserving Watermark for Large Language Models** (ICML 2024) | A key reference for DiP-style detection and robust accessible detection. | https://proceedings.mlr.press/v235/wu24h.html |
| Multi-bit robust watermarking | Qu et al., **Provably Robust Multi-bit Watermarking for AI-generated Text** (USENIX Security 2025) | Strong early multi-bit robustness result using structured assignment and ECC ideas. | https://www.usenix.org/conference/usenixsecurity25/presentation/qu-watermarking |
| ECC-based watermarking | Chao et al., **Watermarking Language Models with Error Correcting Codes** (WMARK@ICLR 2025 / TMLR under review in 2026) | Important because it explicitly frames watermarking as coding theory; useful contrast with your 9991 negative result. | https://openreview.net/forum?id=xetVzmw9dW |

## 2. Papers closest to your 9991 work

| Topic | Paper | Why it matters | Link |
|---|---|---|---|
| Your baseline | Feng et al., **BiMark: Unbiased Multilayer Watermarking for Large Language Models** (ICML 2025) | Your 9991 project was built on this. Keep it as the main inner-layer baseline for 9993. | https://arxiv.org/abs/2506.21602 |
| Dynamic capacity allocation | Lin et al., **DERMARK: A Dynamic, Efficient and Robust Multi-bit Watermark for Large Language Models** (2025) | Important because it explicitly models varying watermark capacity and short/low-entropy text issues. | https://arxiv.org/abs/2502.05213 |
| Majority-bit coding | Xu et al., **Majority Bit-Aware Watermarking For Large Language Models** (2025) | Useful comparison for alternative multi-bit coding strategies and quality-recovery trade-offs. | https://arxiv.org/abs/2508.03829 |

## 3. The newest multi-bit papers that matter most for 9993

| Topic | Paper | Why it matters | Link |
|---|---|---|---|
| Distortion-free multi-bit | Jiang et al., **MirrorMark: A Distortion-Free Multi-Bit Watermark for Large Language Models** (2026) | Very relevant because it couples distortion-free generation with context scheduling and edit resilience. | https://arxiv.org/abs/2601.22246 |
| Short-text multi-bit reliability | Xu et al., **XMark: Reliable Multi-Bit Watermarking for LLM-Generated Texts** (ACL 2026 main) | Extremely important for your project because it explicitly targets the limited-token regime. | https://arxiv.org/abs/2604.05242 |
| Detector statistics | He et al., **On the Empirical Power of Goodness-of-Fit Tests in Watermark Detection** (NeurIPS 2025 spotlight) | Useful if you later strengthen the detector rather than the embedder. | https://openreview.net/forum?id=YES7VDXPV8 |

## 4. Attack papers you must treat as first-class references

| Topic | Paper | Why it matters | Link |
|---|---|---|---|
| Character-level removal | Zhang et al., **Character-Level Perturbations Disrupt LLM Watermarks** (NDSS 2026) | This is crucial. It shows that typo/swap/homoglyph edits can remove watermarks more efficiently by breaking tokenization. | https://www.ndss-symposium.org/ndss-paper/character-level-perturbations-disrupt-llm-watermarks/ |
| Adaptive attack | Huang et al., **RLCracker: Exposing the Vulnerability of LLM Watermarks with Adaptive RL Attacks** (2025) | Strong reminder that robustness claims must be adversarial, not just based on generic paraphrase attacks. | https://arxiv.org/abs/2509.20924 |
| Edit localization | Xie et al., **Detecting Post-generation Edits to Watermarked LLM Outputs via Combinatorial Watermarking** (ICLR 2026 submission) | Relevant because it treats local post-edit detection as its own problem, closely related to synchronization and local corruption. | https://openreview.net/forum?id=SzrQBJDYHn |
| Forgery defense | Aremu et al., **Mitigating Watermark Forgery in Generative Models via Randomized Key Selection** (ICLR 2026 submission) | Useful if you later expand from removal robustness to forgery robustness. | https://openreview.net/forum?id=oSBHt98To6 |

## 5. Diffusion-language-model watermarking papers (important, but stretch goal for you)

| Topic | Paper | Why it matters | Link |
|---|---|---|---|
| First DLM watermark | Gloaguen et al., **Watermarking Diffusion Language Models** (NeurIPS 2025 GenProCC workshop) | Establishes the expectation-based view for DLM watermarking. Good to know, but do not make this your main 9993 line unless AR work is already solid. | https://openreview.net/forum?id=Iw6kgfvsaL |
| Systematic dLLM study / Ripple | Wang et al., **Signed in Ink, Hidden in Noise: Watermarking Diffusion Large Language Models** (ICLR 2026 submission) | Shows how quickly the DLM gap has filled. Good background, but higher replication risk. | https://openreview.net/forum?id=Ovu02vITZN |
| Decoding-guided dLLM watermark | Hong and No, **dMARK: Decoding-Guided Watermarking for Discrete Diffusion Language Models** (ICLR 2026 submission) | Interesting because it uses decoding order rather than token-probability distortion. | https://openreview.net/forum?id=0hdSiZ1br0 |
| Distortion-free DDLM watermark | Bagchi et al., **Watermarking Discrete Diffusion Language Models** (2025/2026 workshop track) | Useful if later you want to transplant distortion-free ideas across AR and DLM families. | https://arxiv.org/abs/2511.02083 |

## 6. Open-source model ownership / model-side watermarking

| Topic | Paper | Why it matters | Link |
|---|---|---|---|
| Open-source model watermark | Bakshi et al., **OpenStamp: A Watermark for Open-Source Language Models** (ICLR 2026 submission) | Model-side watermarking rather than purely inference-time watermarking. Relevant but outside the main thesis scope. | https://openreview.net/forum?id=DU5eTaQSHT |
| Open-source ownership verification | Xue et al., **PRO: Enabling Precise and Robust Text Watermark for Open-Source LLMs** (ICLR 2026 submission) | Useful if you later extend the work toward model ownership or open-source deployment. | https://openreview.net/forum?id=neE8pqIqyR |

## 7. Survey papers for fast re-entry

| Topic | Paper | Why it matters | Link |
|---|---|---|---|
| Broad LLM watermarking survey | Liang et al., **Watermarking techniques for large language models: a survey** (Artificial Intelligence Review, 2026) | Good fast overview, but use it as an entry point rather than your primary technical source. | https://link.springer.com/article/10.1007/s10462-025-11474-6 |
| 2025 survey | Yang et al., **Watermarking for Large Language Models: A Survey** (Mathematics, 2025) | Another overview that is easy to scan before diving back into specific methods. | https://www.mdpi.com/2227-7390/13/9/1420 |

## Bottom-line reading order for you

Read in this exact order if your goal is to move the thesis fastest:

1. BiMark
2. DERMARK
3. XMark
4. MirrorMark
5. Character-Level Perturbations Disrupt LLM Watermarks
6. RLCracker
7. Provably Robust Multi-bit Watermarking for AI-generated Text
8. Watermarking Language Models with Error Correcting Codes
9. GoF tests paper
10. DLM papers only after the above are understood
