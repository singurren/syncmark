# Synthetic preview summary

These results come from the **synthetic IDS-channel simulator**, not from full LLM experiments. They are intended only to validate the synchronization hypothesis before GPU-heavy runs.

Configuration used:

- message bits: 16
- text lengths: 120, 160, 240, 320, 400
- inner flip probability: 0.05
- substitution / deletion / insertion: 0.02 / 0.02 / 0.02
- trials: 50 per setting

## Mean results

|                     |   bit_accuracy |   exact_recovery |   crc_pass |
|:--------------------|---------------:|-----------------:|-----------:|
| ('hamming74', 120)  |          0.676 |             0.14 |       0.26 |
| ('hamming74', 160)  |          0.64  |             0.12 |       0.22 |
| ('hamming74', 240)  |          0.621 |             0.1  |       0.24 |
| ('hamming74', 320)  |          0.559 |             0.06 |       0.32 |
| ('hamming74', 400)  |          0.631 |             0.08 |       0.32 |
| ('repetition', 120) |          0.615 |             0.08 |       0.18 |
| ('repetition', 160) |          0.631 |             0.1  |       0.28 |
| ('repetition', 240) |          0.664 |             0.06 |       0.08 |
| ('repetition', 320) |          0.562 |             0.06 |       0.2  |
| ('repetition', 400) |          0.556 |             0    |       0.1  |
| ('syncmark', 120)   |          0.806 |             0.2  |       0.18 |
| ('syncmark', 160)   |          0.76  |             0.12 |       0.26 |
| ('syncmark', 240)   |          0.774 |             0.12 |       0.26 |
| ('syncmark', 320)   |          0.869 |             0.16 |       0.22 |
| ('syncmark', 400)   |          0.851 |             0.3  |       0.34 |

## Quick interpretation

- The synchronization-aware method is clearly stronger than the repetition baseline in bit accuracy across all tested lengths.
- It also beats the naive Hamming baseline in exact recovery at 120, 320, and 400 marked positions in this preview run.
- The preview is deliberately modest: it demonstrates *mechanistic plausibility*, not final thesis-level performance.
