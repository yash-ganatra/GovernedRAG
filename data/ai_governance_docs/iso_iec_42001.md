# ISO/IEC 42001 — AI Management System Standard

> **Source:** International Organization for Standardization (ISO) / International Electrotechnical Commission (IEC)
> **URL:** https://www.iso.org/standard/81230.html
> **Publication:** ISO/IEC 42001:2023 (First Edition, December 2023)
> **Last Accessed:** 2026-02-24
> **Content Type:** International Standard Summary and Internal Policy Mapping
> **Note:** The full ISO/IEC 42001 standard is copyright-protected. This document provides a structured public-domain summary of the standard's requirements and a governance framework mapping, based on publicly available information and ISO committee publications.
> **Licence:** Summary content is based on publicly available ISO/IEC documentation

---

## Overview

ISO/IEC 42001:2023 is the first international standard that specifies requirements for establishing, implementing, maintaining, and continually improving an **Artificial Intelligence Management System (AIMS)**. It follows the high-level structure (HLS / Annex SL) common to ISO management systems such as ISO 27001 (Information Security) and ISO 9001 (Quality). Organisations can use ISO/IEC 42001 to demonstrate responsible AI development and deployment and to align with regulatory requirements including the EU AI Act and GDPR.

---

## Standard Structure (Clauses 1–10)

ISO/IEC 42001 is organised into 10 clauses following the Plan-Do-Check-Act (PDCA) model:

| Clause | Title | PDCA Phase |
|--------|-------|-----------|
| 1 | Scope | — |
| 2 | Normative References | — |
| 3 | Terms and Definitions | — |
| 4 | Context of the Organisation | Plan |
| 5 | Leadership | Plan |
| 6 | Planning | Plan |
| 7 | Support | Do |
| 8 | Operation | Do |
| 9 | Performance Evaluation | Check |
| 10 | Improvement | Act |

---

## Clause 4 — Context of the Organisation

### 4.1 Understanding the Organisation and Its Context

The organisation shall determine external and internal issues relevant to its AI purpose and that affect its ability to achieve the intended outcomes of its AIMS. This includes:

- The organisation's role(s) in the AI value chain (developer, deployer, provider of AI components)
- Legal, regulatory, and contractual requirements applicable to AI
- Stakeholder expectations regarding responsible AI
- The intended use cases and deployment contexts of AI systems

### 4.2 Understanding Needs and Expectations of Interested Parties

The organisation shall determine:

- Interested parties relevant to the AIMS (employees, customers, regulators, affected communities)
- Relevant requirements of those interested parties
- Which of those requirements are addressed through the AIMS

### 4.3 Determining the Scope of the AIMS

The organisation shall determine the boundaries and applicability of the AIMS, including:

- Which AI systems and processes are in scope
- Interfaces and dependencies with other management systems
- Exclusions and their justifications

### 4.4 AI Management System

The organisation shall establish, implement, maintain, and continually improve an AIMS, including the processes needed and their interactions, in accordance with the requirements of ISO/IEC 42001.

---

## Clause 5 — Leadership

### 5.1 Leadership and Commitment

Top management shall demonstrate leadership and commitment with respect to the AIMS by:

- Ensuring AI policy and AI objectives are established and compatible with the strategic direction of the organisation
- Integrating AIMS requirements into business processes
- Ensuring resources for the AIMS are available
- Communicating the importance of effective AI risk management
- Directing and supporting persons to contribute to the effectiveness of the AIMS
- Promoting continual improvement
- Supporting other relevant management roles to demonstrate their leadership

### 5.2 AI Policy

Top management shall establish an AI policy that:

**(a)** Is appropriate to the purpose of the organisation

**(b)** Includes a commitment to satisfy applicable requirements related to AI

**(c)** Includes a commitment to continual improvement of the AIMS

**(d)** Includes commitments to responsible AI including fairness, transparency, accountability, and human oversight

The AI policy shall be:
- Available as documented information
- Communicated within the organisation
- Available to interested parties, as appropriate

### 5.3 Organisational Roles, Responsibilities and Authorities

Top management shall ensure that the responsibilities and authorities for relevant roles are assigned and communicated within the organisation including:

- Who is responsible for ensuring the AIMS conforms to the standard requirements
- Who reports to top management on the performance of the AIMS
- Who is responsible for each individual AI system's risk management activities

---

## Clause 6 — Planning

### 6.1 Actions to Address Risks and Opportunities

When planning for the AIMS, the organisation shall consider internal and external issues, interested party requirements, and determine the risks and opportunities that need to be addressed.

The organisation shall plan:
- Actions to address risks and opportunities related to AI systems
- How to integrate and implement the actions into AIMS processes
- How to evaluate the effectiveness of these actions

### 6.2 AI Objectives and Planning to Achieve Them

The organisation shall establish AI objectives at relevant functions and levels. AI objectives shall:

- Be consistent with the AI policy
- Be measurable (where practicable)
- Take into account applicable requirements relating to AI systems
- Be monitored and updated as appropriate

**Examples of AI objectives:**
- Achieve >95% accuracy on production models with bias testing across demographic groups
- All AI systems subject to DPIA before deployment
- Zero unresolved high-severity AI incidents per quarter
- 100% of AI system decisions are explainable upon request within 72 hours

### 6.1.2 AI Risk Assessment

The organisation shall define and apply an AI risk assessment process that:

- Establishes AI risk acceptance criteria
- Ensures that repeated AI risk assessments produce consistent, valid and comparable results
- Identifies AI risks and the assets that these risks are associated with
- Analyses and evaluates AI risks for likelihood and consequence
- Prioritises risk treatment

**AI Risk Categories to Assess:**

| Risk Category | Examples |
|--------------|---------|
| Safety risks | Physical harm from AI-controlled systems |
| Fairness risks | Discriminatory outcomes in high-stakes decisions |
| Privacy risks | Unauthorised access to personal data via AI |
| Transparency risks | Unexplainable decisions affecting individuals |
| Operational risks | Model drift, service disruption |
| Reputational risks | Public harm from AI system failures |
| Legal/compliance risks | Violations of GDPR, EU AI Act |

---

## Clause 7 — Support

### 7.1 Resources

The organisation shall determine and provide the resources needed for the establishment, implementation, maintenance, and continual improvement of the AIMS.

### 7.2 Competence

The organisation shall:
- Determine the necessary competence of persons working under its control that affects AI performance and risk management
- Ensure those persons are competent based on education, training, or experience
- Take actions to acquire the necessary competence
- Retain appropriate documented evidence of competence

AI-specific competence requirements include:
- Understanding of AI/ML development and testing practices
- Knowledge of applicable AI regulations (EU AI Act, GDPR)
- Data governance and data quality management
- AI ethics and fairness assessment methods

### 7.3 Awareness

Persons working under the organisation's control shall be aware of:
- The AI policy
- Their contribution to the effectiveness of the AIMS
- The implications of not conforming to AIMS requirements
- Specific risks associated with AI systems they work with

### 7.4 Communication

The organisation shall determine the need for internal and external communications relevant to the AIMS including:
- What to communicate (AI risks, incidents, policy updates)
- When to communicate
- With whom to communicate
- How to communicate

### 7.5 Documented Information

The AIMS shall include documented information required by ISO/IEC 42001 and determined by the organisation as necessary. Required documentation includes:

**Mandatory Documents:**
- AIMS scope (4.3)
- AI policy (5.2)
- AI risk assessment results (6.1.2)
- AI risk treatment plan (6.1.3)
- AI objectives (6.2)
- AI system lifecycle documentation (8.4)
- Results of monitoring and measurement (9.1)
- Internal audit results (9.2)
- Management review results (9.3)
- Nonconformities and corrective actions (10.1)

---

## Clause 8 — Operation

### 8.1 Operational Planning and Control

The organisation shall plan, implement, control, monitor, and review processes needed to meet requirements for the provision of AI products and services and to implement the actions determined in Clause 6.

### 8.2 AI Risk Assessment (Operational)

The organisation shall perform AI risk assessments at planned intervals or when significant changes are proposed or occur in AI systems.

### 8.3 AI Risk Treatment

The organisation shall implement the AI risk treatment plan and retain documented evidence of the results.

### 8.4 AI System Lifecycle

The standard addresses the full AI lifecycle including:

**Design and Development:**
- Define requirements for AI systems including data requirements
- Apply data governance practices
- Document model selection rationale and architecture decisions

**Deployment:**
- Test AI systems in conditions approximating deployment
- Establish monitoring and alerting for production systems
- Obtain required approvals before deployment

**Operations:**
- Monitor performance, fairness, and security in production
- Detect and respond to anomalies and incidents
- Maintain logs sufficient for audit and investigation

**Decommissioning:**
- Plan for safe retirement of AI systems
- Handle personal data disposal in compliance with GDPR
- Document lessons learned

---

## Clause 9 — Performance Evaluation

### 9.1 Monitoring, Measurement, Analysis, and Evaluation

The organisation shall evaluate AI performance by:
- Determining what needs to be monitored and measured
- Determining methods for monitoring, measurement, analysis and evaluation
- Determining when monitoring and measuring shall be performed
- Analysing and evaluating monitoring and measurement results

**Key AI Performance Metrics:**

| Metric | Description |
|--------|-------------|
| Model accuracy | Performance on validation datasets |
| Fairness indicators | Demographic parity, equal opportunity |
| Data quality | Coverage, completeness, and accuracy |
| Incident rate | Frequency and severity of AI failures |
| Explainability score | % of decisions explainable upon request |
| Compliance posture | Open audit findings and remediation status |

### 9.2 Internal Audit

The organisation shall conduct internal audits at planned intervals to provide information on whether the AIMS:
- Conforms to the organisation's own requirements for its AIMS
- Conforms to the requirements of ISO/IEC 42001
- Is effectively implemented and maintained

### 9.3 Management Review

Top management shall review the organisation's AIMS at planned intervals to ensure its continuing suitability, adequacy, and effectiveness. Reviews shall include outcomes of AI risk assessments, performance against objectives, and resource adequacy.

---

## Clause 10 — Improvement

### 10.1 Nonconformity and Corrective Action

When a nonconformity occurs (AI system misbehaviour, policy breach, audit finding), the organisation shall:

- React to the nonconformity and take action to control and correct it
- Evaluate the need to eliminate the causes of nonconformity
- Implement any action needed
- Review the effectiveness of any corrective action taken
- Update risks and opportunities if necessary
- Make changes to the AIMS if necessary

### 10.2 Continual Improvement

The organisation shall continually improve the suitability, adequacy, and effectiveness of the AIMS.

---

## Alignment with Other Standards and Regulations

| ISO/IEC 42001 Clause | EU AI Act Alignment | GDPR Alignment | NIST AI RMF |
|----------------------|--------------------|--------------------|-------------|
| 5.2 AI Policy | Article 9 (Quality management) | Article 24 (Accountability) | GV-1.6 |
| 6.1.2 Risk Assessment | Article 9 (Risk management) | Article 35 (DPIA) | MS-1.1 |
| 7.5 Documentation | Article 11 (Technical documentation) | Article 30 (Records) | GV-1.6 |
| 8.4 Lifecycle | Articles 9, 17 (Lifecycle requirements) | Article 25 (Privacy by design) | GV-1.7 |
| 9.1 Monitoring | Article 72 (Post-market monitoring) | Article 5(2) (Accountability) | MS-3.1 |
| 10.1 Corrective Action | Article 20 (Corrective actions) | Article 33 (Breach notification) | MS-4.2 |
