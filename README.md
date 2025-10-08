# ThreatForge 🔒  
**Breaking the Chain: Discovering Risks in Function‑Orchestrated Workflows of LLM‑Integrated Frameworks**

---

## 📘 Overview
**ThreatForge** is a systematic static–dynamic analysis framework that uncovers over‑privileged monitoring functions and workflow‑level security risks in LLM‑Integrated Frameworks (LIFs) such as **LangChain**, **LlamaIndex**, **Semantic Kernel**, **AutoGPT**, and **CrewAI**.

Large Language Model‑integrated frameworks orchestrate prompts, API calls, and external tools to simplify LLM‑based application development. However, this orchestration also introduces new attack surfaces beyond the models themselves—allowing hidden privilege escalations or unintentional data leakage.  
ThreatForge automates the discovery of these threats through cross‑framework analysis and reproducible evaluation.

---

## 🚀 Features
- **Static + Dynamic Analysis Pipeline** – Automatically identifies event‑triggered monitoring functions that may misuse data or framework privileges.  
- **Cross‑Framework Coverage** – Supports five major LLM frameworks (LangChain, LlamaIndex, Semantic Kernel, AutoGPT, CrewAI).  
- **Payload‑Driven Validation** – Simulates controlled injection tests to verify if a function exhibits over‑privileged behavior.  
- **Security Insight Generation** – Generates empirical security metrics (over‑privilege ratio, function enumeration, runtime profiling).  

---

## 🧰 System Architecture
ThreatForge’s pipeline includes:
1. **Candidate Identification** – Extracts event‑triggered monitoring functions from framework source code and metadata.  
2. **Payload Construction** – Builds controlled test payloads according to function parameter priorities.  
3. **Dynamic Injection + Instrumentation** – Executes hooks in sandbox mode to capture runtime behaviors.  
4. **Verification & Detection** – Determines over‑privileged functions by analyzing access to sensitive domains (`API keys`, `model outputs`, `device access`, `session metadata`).  

Algorithmic details are described in **Algorithm 1: ThreatForge Pipeline**.

---

## 📊 Evaluation Summary
ThreatForge analyzed **9,928** event‑triggered functions across the five frameworks and identified **168 monitoring hooks**, among which **75 exhibited over‑privileged behaviors**.  
These results highlight that while most framework functions are benign, nearly half of the monitoring hooks grant excessive privileges—underscoring the need for least‑privilege enforcement in framework design.

| Framework | Event‑Triggered | Monitoring | Over‑Privileged | Ratio |
|------------|----------------|-------------|-----------------|--------|
| LangChain | 2,316 | 31 | 14 | 47.37 % |
| LlamaIndex | 2,180 | 34 | 14 | 41.18 % |
| Semantic Kernel | 2,373 | 22 | 9 | 40.91 % |
| AutoGPT | 2,286 | 43 | 23 | 53.49 % |
| CrewAI | 773 | 38 | 11 | 28.95 % |

---

## ⚙️ Installation
```bash
# Clone this repository
git clone https://github.com/anonymous-123741/ThreatForge.git
cd ThreatForge

# (Optional) Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
