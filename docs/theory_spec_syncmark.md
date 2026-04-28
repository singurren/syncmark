# Theory specification: SyncMark

## 1. Research question

The central question is:

> In short LLM-generated texts exposed to realistic post-generation edits, is the dominant recovery failure caused by ordinary bit corruption, or by **synchronization loss** induced by insertion/deletion/tokenization drift?

This package adopts the second view and treats multi-bit watermark recovery as decoding over an **insertion-deletion-substitution (IDS) channel** rather than over an i.i.d. bit-flip channel.

---

## 2. Problem setup

Let the original watermarked continuation be a token sequence

\[
X = (x_1, x_2, \dots, x_T).
\]

The embedder wishes to encode a message

\[
m \in \{0,1\}^B.
\]

After human or model editing, we observe a modified sequence

\[
Y = (y_1, y_2, \dots, y_{T'}), \quad T' \neq T \text{ in general.}
\]

Existing short-text multi-bit work often behaves as if decoding errors arise mainly from substitutions or noisy votes. But under realistic editing, the effective channel also includes:

- **deletions** of tokens or spans,
- **insertions** of extra words or symbols,
- **substitutions** or paraphrases,
- **character-level perturbations** that change tokenization boundaries.

Therefore the channel is better approximated by

\[
W_{IDS}: X \rightarrow Y,
\]

rather than by a pure binary symmetric channel.

---

## 3. Why naive ECC can fail in short texts

Suppose an inner watermark produces a local binary observation at each usable token position. Let the total number of usable positions be \(N\), and let a message of length \(B\) be spread approximately evenly across positions. Then each message bit receives about

\[
N/B
\]

independent or weakly dependent votes.

If each local vote is correct with probability \(q > 1/2\), the majority-vote bit error roughly satisfies a Chernoff-style decay

\[
P_e^{\text{raw}} \lesssim \exp\big(-2(q-1/2)^2 N/B\big).
\]

Now suppose we replace the message with an ECC-expanded codeword of length \(B' > B\) while keeping the same text length budget \(N\). The average votes per encoded bit become

\[
N/B' = (B/B')\cdot (N/B).
\]

So the raw encoded-bit reliability decreases exponentially in the redundancy factor. In long texts, ECC may still help. In short texts, however, redundancy can **dilute the per-bit evidence so much that the decoder never reaches the ECC correction radius**.

This explains the key negative observation from your 9991 report: when the text budget is finite, adding a standard ECC on top of a vote-based inner watermark does not automatically help.

---

## 4. Core idea of SyncMark

SyncMark changes the role of redundancy.

Instead of spending all redundancy on parity protection, it spends part of the redundancy on **synchronization anchors**.

### 4.1 Outer frame

The message is first extended with a lightweight checksum

\[
\tilde m = [m \; || \; c(m)].
\]

Then we construct repeated cycles of the form

\[
A_r \; || \; \tilde m,
\]

where:

- \(A_r\) is an anchor pattern unique to cycle \(r\), generated from a secret key,
- \(\tilde m\) is the payload-plus-checksum block.

For a target text length \(T\), the outer stream is truncated to the first \(T\) positions.

### 4.2 Local embedding

At each position \(t\), the inner watermark tries to bias generation toward the target bit \(s_t\) from the frame stream. In the research prototype inside this package, the inner layer is a simple keyed partition-based bias. In the actual thesis, this inner layer should be replaced by your BiMark implementation or another lower-distortion watermark.

### 4.3 Detection as alignment, then voting

The detector extracts a noisy observed bit stream

\[
\hat s = (\hat s_1, \hat s_2, \dots, \hat s_{T'}).
\]

Rather than assigning \(\hat s_t\) to payload bits only by absolute position, SyncMark solves an alignment problem between the observed stream and the expected anchor+payload layout.

The decoder uses a dynamic-programming score:

\[
\text{score} = \sum \text{match rewards} - \sum \text{gap penalties},
\]

with stronger rewards/penalties on anchor positions than on payload positions. After alignment, all observations aligned to payload slot \(j\) are aggregated and majority-decoded.

This yields a two-stage decomposition:

1. **Recover synchronization** using anchors.
2. **Recover payload** using repeated aligned evidence.

---

## 5. Formal decomposition of the error event

Let

- \(E_{sync}\) be the event that anchor alignment fails,
- \(E_{payload}\) be the event that payload decoding fails given successful alignment.

Then

\[
P(E_{total}) \le P(E_{sync}) + P(E_{payload} \mid E_{sync}^c).
\]

This decomposition is the main theoretical motivation of the project.

Naive ECC mostly targets \(P(E_{payload})\).
SyncMark first attacks \(P(E_{sync})\), which is often the dominant term under insertion/deletion and tokenization drift.

---

## 6. Why anchors help more than naive parity under edits

Consider an edit that deletes one token early in the sequence. Without synchronization recovery, all later absolute positions become offset by one, causing many later local observations to vote for the wrong bit index. This creates a **global decoding failure from a local edit**.

Anchors change this failure geometry. If the decoder can re-lock onto the next anchor, the damage is localized to the corrupted region rather than propagated to the rest of the sequence.

In other words, anchors trade some payload rate for **damage containment**.

---

## 7. Channel model for real attacks

For the thesis experiments, we recommend using three increasingly realistic channels:

### Channel A: substitution-only noise

A standard binary corruption model to establish basic sanity.

### Channel B: token-level IDS edits

Random deletion, insertion, and substitution at token level.

### Channel C: character-level tokenization drift

Typo/swap/homoglyph/unicode perturbations that modify the tokenizer's segmentation. This is the most important threat model because recent work shows it is highly effective against existing watermarks.

---

## 8. Hypotheses

### H1: synchronization dominates under realistic edits

Under token insertion/deletion and char-level attacks, most recovery loss for short texts will come from synchronization drift rather than from ordinary bit flips.

### H2: SyncMark improves exact recovery at fixed text budget

At the same message length and text length, SyncMark should outperform:

- plain repeated multi-bit assignment,
- plain ECC without synchronization recovery,
- and ideally BiMark + naive ECC.

### H3: gains are strongest in the 100-300 token regime

As texts get shorter, per-bit vote budgets shrink and desynchronization becomes relatively more harmful, so anchor-aware decoding should help most there.

---

## 9. What would falsify the theory?

The theory would be weakened if the following happens in full LLM experiments:

1. SyncMark does **not** beat naive ECC once text quality is matched.
2. Character-level attacks do **not** create larger gains for synchronization-aware decoding than paraphrase-only attacks.
3. Replacing the reference inner marker with BiMark removes the gain entirely.

If these occur, the real bottleneck may be local signal strength rather than synchronization.

---

## 10. Main contribution claim for a paper

A concise paper-level claim would be:

> We show that exact multi-bit recovery in short edited LLM text is limited less by conventional error correction than by synchronization loss. We propose a synchronization-aware outer framing and alignment decoder that improves recovery under insertion, deletion, and character-level post-editing attacks.

This claim is modest, falsifiable, and closely connected to your 9991 negative results.
