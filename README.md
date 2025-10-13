# ThreatForge 
**Breaking the Chain: Discovering Risks in Function‑Orchestrated Workflows of LLM‑Integrated Frameworks**

---

## Overview
**ThreatForge** is a systematic static–dynamic analysis framework that uncovers over‑privileged monitoring functions and workflow‑level security risks in LLM‑Integrated Frameworks (LIFs) such as **LangChain**, **LlamaIndex**, **Semantic Kernel**, **AutoGPT**, and **CrewAI**.

---

## Features
- **Static + Dynamic Analysis Pipeline** – Automatically identifies event‑triggered monitoring functions that may misuse data or framework privileges.  
- **Cross‑Framework Coverage** – Supports five major LLM frameworks (LangChain, LlamaIndex, Semantic Kernel, AutoGPT, CrewAI).  
- **Payload‑Driven Validation** – Simulates controlled injection tests to verify if a function exhibits over‑privileged behavior.  
- **Security Insight Generation** – Generates empirical security metrics (over‑privilege ratio, function enumeration, runtime profiling).  

---

## System Architecture
ThreatForge’s pipeline includes:
1. **Candidate Identification** – Extracts event‑triggered monitoring functions from framework source code and metadata.  
2. **Payload Construction** – Builds controlled test payloads according to function parameter priorities.  
3. **Dynamic Injection + Instrumentation** – Executes hooks in sandbox mode to capture runtime behaviors.  
4. **Verification & Detection** – Determines over‑privileged functions by analyzing access to sensitive domains (`API keys`, `model outputs`, `device access`, `session metadata`). 
