**DELIVERY CURRICULUM**

**AI-Augmented Product Security**

*Using AI to secure products — and securing products that use AI*

| FORMAT 3-day hands-on intensive | STRUCTURE 9 applied modules by Ajinkya | AUDIENCE Product Security / AppSec |
| :---- | :---- | :---- |

**By Ajinkya Kolhe  |**  [AI Training Resume](https://docs.google.com/document/d/1IK8wIebJ7JL0qQuS2zoYBPgGO-T-um3i/edit)


**Teaching sequence.** Participants are practising Product Security engineers. Every module provides a quick refresher of the standard workflow without AI, a short unaided baseline, then a detailed AI-assisted code-along with independent verification. The primary learning goal is better execution of their existing jobs with AI. Chronos is the lab; the workflow transfers to their own products and toolchains.

**Programme Overview**

This hands-on programme prepares Product Security engineers for two connected responsibilities: using AI as a working instrument across threat modeling, platform discovery, code review, triage, penetration testing and automation; and assessing the new attack surfaces introduced by LLM, RAG and agentic applications. Participants work on unfamiliar platforms as readily as systems they already own, while treating every model output as a hypothesis that must be supported by inspectable evidence.

The programme combines conventional AppSec practice with OWASP GenAI risks and other such frameworks. The curriculum maintains two connected lenses throughout: AI-augmented security work and security assessment of AI-enabled products. Supply-chain assurance, MITRE ATLAS-mapped attack patterns and lifecycle AI governance are applied across the same workflow. In each lab, participants establish a human baseline, use AI on the same task, compare coverage and errors, and verify the result themselves.

**Learning Outcomes**

* Apply AI across the Product Security lifecycle while retaining the security method and final human judgment.

* Reconstruct conventional and AI-enabled architectures, data flows, trust boundaries and review hotspots with evidence.

* Threat-model, review and assess LLM, RAG and agentic systems using repeatable methods and MITRE ATLAS-mapped patterns.

* Validate findings, compare human and AI work, reduce false positives and support auditable approvals and release decisions.

**Audience and Prerequisites**

**Audience.** Practising Product Security and AppSec engineers reviewing one or more platforms.

**Foundation.** Working knowledge of OWASP Top 10, common vulnerability classes, CWE/CVSS and secure design principles; ability to read Java, Python or TypeScript; basic API and cloud familiarity.

**Lab controls.** All attack activity uses sanctioned synthetic targets. No live customer systems, production credentials or sensitive customer data are used. The common application will include a working chatbot, RAG capability, agent and MCP server before delivery.

**Reference frameworks.** [OWASP LLM & GenAI](https://genai.owasp.org/initiatives/top-10-for-llm-and-genai/)  |  [MITRE ATLAS](https://atlas.mitre.org/)

**DAY 1  |  Understand and Reason with AI**

**Module 1 — AI as a Product Security Copilot**

**Objective.** Establish where AI extends the engineer, where it fails and how evidence-based verification governs its use.

* AI across threat modeling, code review, triage, testing and automation; context-bounded models, hallucinated findings, sensitive-data handling and human accountability.

* Reviewer stance, task decomposition, curated context, structured findings with CWE, severity, location, evidence, reproduction path and confidence; prompt regression checks.

* Human foundation: trace vulnerable behavior, distinguish model analysis from verified evidence and retain authorization and severity judgment.

**BUILD  Review a function unaided, then use AI to propose findings. Compare coverage and errors; verify one real flaw and reject one unsupported claim.**

**Module 2 — AI-Assisted Platform Discovery and Security Mapping**

**Objective.** Onboard cold to an unfamiliar repository and produce an evidence-grounded map of conventional and AI components.

* File-tree triage, dependency graphing, hierarchical summarisation, repository retrieval and agentic navigation within context limits.

* Entrypoints, services, stores, identity flows and sensitive-data paths; AI-BOM/SBOM with model, provider, dataset, package and tool provenance.

* Human foundation: understand request paths, identity, data ownership and trust boundaries well enough to challenge an AI-generated map.

**BUILD  Map one request manually, then use AI for broader discovery. Compare maps, inspect the cited source and rank review hotspots.**

**Module 3 — AI-Assisted Threat Modeling and Design Review**

**Objective.** Build a principle-based threat model grounded in the reconstructed platform rather than generic AI-risk boilerplate.

* STRIDE for application threats; MITRE ATLAS for AI attack patterns; OWASP GenAI risks for application failure patterns.

* Abuse cases, attack trees, technique-to-control mapping, residual risk and coverage comparison against a reference model.

* Human foundation: identify assets, attacker goals, plausible paths and control effectiveness before accepting model-generated threats.

**BUILD  Threat-model a flow unaided, then use AI to expand abuse cases. Compare coverage, reject inapplicable threats and map valid paths to controls.**

**DAY 2  |  Find and Validate with AI**

**Module 4 — AI-Assisted Secure Code and Business-Logic Review**

**Objective.** Find business-logic and AI-integration flaws through hypothesis-driven analysis, each traced to implementation evidence.

* Trace identity and data flows, formulate abuse hypotheses, inspect implementation and record a reproducible evidence trail.

* IDOR, state-machine abuse, cross-service authorisation, prompt construction, RAG access control, tenant isolation and tool permissions.

* Human foundation: understand authorization invariants, business rules and source-to-sink behavior before accepting a finding.

**BUILD  Review a curated change manually, then use AI to trace flows and propose flaws. Compare findings, reproduce real issues and reject false alarms.**

**Module 5 — AI-Assisted Vulnerability Triage and Risk Prioritisation**

**Objective.** Triage scanner and AI-assessment output at scale while reducing false positives and maintaining an auditable evidence standard.

* SARIF ingestion, normalisation, de-duplication, reachability, exploitability and business-context enrichment across SAST, SCA and DAST.

* Authoritative CVE verification, resistance to prompt injection in untrusted reports, separate scores for evidence, impact and uncertainty.

* Human foundation: judge reachability, exploitability, business impact, evidence strength and escalation thresholds.

**BUILD  Triage a small sample manually, then use AI on the noisy evidence set. Compare precision and time, verify advisories and prioritize cases.**

**Module 6 — AI-Assisted Security Testing and Investigation**

**Objective.** Validate review hypotheses through bounded API and runtime evidence rather than accepting model claims.

* Use AI to understand endpoints, generate candidate tests, manipulate requests, interpret responses and construct reproduction steps.

* Test identity, authorization, business state and input boundaries against observed behavior and documented security requirements.

* Human foundation: understand HTTP behavior, expected access rules and what an observed response actually proves.

**BUILD  Write baseline API tests unaided, then use AI to generate additional cases. Run both sets, compare coverage and reproduce or reject findings.**

**DAY 3  |  Operationalise and Assess AI**

**Module 7 — AI-Assisted Remediation, DevSecOps and Security Workflow**

**Objective.** Move from finding to fix, regression evidence and auditable closure with approval before consequential action.

* Use AI to explain findings to developers, propose minimal fixes, generate regression tests, review changes and prepare tickets.

* Connect Git and CI with SAST, SCA, secrets, tests, AI enrichment, policy gates, rescanning and human approval.

* Human foundation: define the security invariant, assess unintended effects and decide whether the fix and evidence justify closure.

**BUILD  Design a fix and acceptance criteria manually, then use AI to propose code and tests. Review the diff, run the gate and compare results.**

**Module 8 — Product Security for AI Applications**

**Objective.** Understand modern AI application architecture and turn new trust boundaries into reviewable security assertions.

* LLM APIs, RAG, embeddings, vector stores, agent tools, MCP, memory, gateways and model supply chains with provenance.

* Prompt injection, disclosure, poisoning, excessive agency, retrieval weaknesses and cost abuse; least privilege and deterministic controls.

* Human foundation: identify untrusted content, data authorization and tool authority independently of an AI-generated inventory.

**BUILD  Map one AI request manually, then use AI to inventory the chatbot, RAG, agent and MCP server. Compare maps and inspect trust boundaries.**

**Module 9 — AI Security Assessment and Release Readiness**

**Objective.** Run a bounded, repeatable assessment of the AI-enabled product and turn evidence and control results into a release decision.

* MITRE ATLAS-informed enumeration, direct and indirect prompt injection, RAG poisoning, cross-user leakage, tool abuse and cost amplification.

* Controls for retrieval authorization, tenant isolation, provenance, least-privilege tools, argument validation, action allowlists and approval.

* Human foundation: judge threat relevance, exploit reproducibility, control sufficiency, residual risk and release accountability.

**BUILD  Design baseline attack tests manually, then use AI to generate and mutate tests across the four AI features. Compare coverage, validate two paths and recommend release conditions.**
