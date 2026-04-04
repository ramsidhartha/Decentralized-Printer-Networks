# Verifiable Decentralized Manufacturing — Research + MVP

> ACM-VIT Research Project | Blockchain Track

---

## Problem

A centralized server manages a queue of print jobs routed to 3D printers owned by independent operators. The connection between server and printer is the attack surface. Two threats:

1. **False completion** — a printer or tampered connection returns a "done" signal without real work happening
2. **Payload breach** — the design file (G-code / CAD) is intercepted and leaked in transit

**Constraints:** You do not own the printers. You cannot modify their internals. You can build an overlay system on top.

---

## Context

- **Domain:** Decentralized 3D-print network for medical device prototyping
- **Client:** A med-tech startup outsourcing prototype prints to independent print farms
- **Threat model:** Faulty or adversarial machines, tampered server-printer connection
- **Decentralization scope:** Verification layer only — not task delegation. Manufacturing stays at known facilities. The blockchain distributes trust in the verification record, not the job routing.

---

## Architecture

Three layers sit on top of the existing printer infrastructure:

```
Client (med-tech startup)
    └── uploads CAD → system slices to G-code → encrypts → posts job hash to chain
            ↓ encrypted G-code over network
Edge Gateway (your overlay — acts as PLC)
    ├── decrypts G-code over short local cable to printer
    ├── runs snapshot commitment engine during execution
    ├── post-print: captures output geometry → computes feature hash
    └── submits all hashes to smart contract
            ↓
Printer (untouched, untrusted)
            ↓ physical output
Simulated Sensors (power, thermal, acoustic, camera)
    └── feed raw time-series into snapshot engine
            ↓
Blockchain (Ethereum Sepolia testnet)
    └── smart contract: checks snapshots + geometry hash → records result
```

---

## Threat 1 — False Completion: Snapshot Commitment Protocol

**Core idea:** At random intervals during execution, the edge gateway samples the simulated sensor stream, hashes the reading plus job ID plus timestamp, and commits it to the chain. The sampling schedule is committed to the chain *before* execution begins — the prover cannot know when samples will be taken.

**Three independent verification signals:**

| Signal | What it checks | Primitive |
|---|---|---|
| Snapshot commitments | Real physical activity at sampled moments | SHA-256 + blockchain |
| Output geometry hash | Physical output matches expected geometry | Perceptual hash / feature vector |

**Formal guarantee:** Probability of successfully faking `n` random snapshots decreases exponentially in `n`. The bound is computable given the sampling rate and sensor modalities.

**Note on geometry hashing:** A cryptographic hash is not used for geometry comparison — manufacturing has inherent physical variance. A perceptual hash or feature vector with a tolerance threshold is used instead.

---

## Threat 2 — Payload Breach: Layered Protection

| Layer | Mechanism |
|---|---|
| Channel encryption | AES-256. Ciphertext travels over open network. Plaintext only on short local cable between gateway and printer |
| Minimal exposure | Full CAD never leaves client domain. Printer only receives encrypted G-code blob + job ID |
| Hash-anchored integrity | Job hash committed to chain before transmission. Gateway verifies hash on receipt. Tampered payload detected before decryption |
| Side-channel constraint | Raw sensor data never committed to chain — only derived feature hashes. Prevents geometry reconstruction from on-chain data |
| Physical copy deterrence | Tamper-detectable sub-surface markers embedded in print geometry. Copies produce hash mismatches against ledger record |

---

## What is Novel Over Prior Work

This project extends [Chiu et al. 2023 — *Verifiable Manufacturing Using Blockchain*](https://arxiv.org/abs/2302.13353) which:
- Proved correct state sequence execution via ZKP on a trusted PLC
- Left the trusted PLC assumption explicit and unresolved
- Did not address payload confidentiality

**Our contribution:** Remove the trusted PLC assumption by grounding verification in externally observed sensor data and output geometry matching — making the system robust to faulty or adversarial machines.

> *We extend the paper's verifiable manufacturing framework by grounding the state sequence in externally observed sensor data, removing the trusted PLC assumption and making the system robust to faulty or adversarial machines.*

---

## Tech Stack

| Component | Technology |
|---|---|
| Sensor simulation | Python — realistic time series for power, thermal, acoustic |
| Edge gateway / overlay | Python |
| Snapshot commitment engine | Python + hashlib SHA-256 |
| Payload encryption | PyCryptodome AES-256 |
| Blockchain | Ethereum Sepolia testnet |
| Smart contract | Solidity |
| Chain interaction | Web3.py |
| Output geometry verification | Simulated feature vector comparison in Python |

---

## MVP Demonstration Scenarios

Three scenarios prove the verification logic end to end:

1. **Legitimate job** — sensor stream matches expected profile → snapshots pass → geometry hash matches → chain records completion
2. **Fake completion** — sensor stream shows no activity → snapshots fail → chain rejects → job marked tampered
3. **Tampered payload** — hash mismatch at gateway on receipt → job rejected before reaching printer

---

## Future Work

Replace snapshot commitments with **FSM + ZKP** using [gnark](https://github.com/ConsenSys/gnark):
- Define the 3D printer FSM formally — heating, printing layer-by-layer, cooling, completion
- Express as an arithmetic circuit
- Generate a zk-SNARK proof per job
- Upgrade from probabilistic guarantee to formal computational proof

This is the path to a publication-grade security argument. The snapshot approach is the tractable MVP. The ZKP extension is the research ceiling.

---

## References

- Chiu et al. (2023). *Verifiable Manufacturing Using Blockchain.* arXiv:2302.13353
- Gennaro et al. (2010). *Non-interactive Verifiable Computing.*
- gnark — Go ZKP library: github.com/ConsenSys/gnark
- Hyperledger Fabric — permissioned blockchain framework