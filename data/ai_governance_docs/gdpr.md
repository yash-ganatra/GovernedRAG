# General Data Protection Regulation (GDPR) — Key Articles for AI Governance

> **Source:** European Parliament and Council of the European Union
> **URL:** https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679
> **Last Accessed:** 2026-02-24
> **Content Type:** Official EU Regulation (EU) 2016/679
> **Jurisdiction:** European Union / UK GDPR (post-Brexit equivalent)
> **Licence:** © European Union, 1998–2024

---

## Overview

The General Data Protection Regulation (GDPR), Regulation (EU) 2016/679, is the primary data protection law in the European Union. It directly intersects with AI governance through three key articles: Article 5(2) on the Accountability Principle, Article 15 on the Right of Access by the Data Subject, and Article 22 on Automated Individual Decision-Making, including Profiling. These articles impose obligations on organisations using AI systems that process personal data.

---

## Article 5 — Principles Relating to Processing of Personal Data

### Article 5(1): The Six Core Principles

Personal data shall be:

**(a) Lawfulness, fairness and transparency** — processed lawfully, fairly and in a transparent manner in relation to the data subject ('lawfulness, fairness and transparency')

**(b) Purpose limitation** — collected for specified, explicit and legitimate purposes and not further processed in a manner that is incompatible with those purposes ('purpose limitation')

**(c) Data minimisation** — adequate, relevant and limited to what is necessary in relation to the purposes for which they are processed ('data minimisation')

**(d) Accuracy** — accurate and, where necessary, kept up to date; every reasonable step must be taken to ensure that personal data that are inaccurate, having regard to the purposes for which they are processed, are erased or rectified without delay ('accuracy')

**(e) Storage limitation** — kept in a form which permits identification of data subjects for no longer than is necessary for the purposes for which the personal data are processed ('storage limitation')

**(f) Integrity and confidentiality** — processed in a manner that ensures appropriate security of the personal data, including protection against unauthorised or unlawful processing and against accidental loss, destruction or damage, using appropriate technical or organisational measures ('integrity and confidentiality')

### Article 5(2): The Accountability Principle

The controller shall be responsible for, and be able to **demonstrate compliance** with, paragraph 1 ('accountability').

**Practical Implications for AI Systems:**

The accountability principle requires organisations deploying AI systems to:

- Maintain records of processing activities involving AI (Article 30)
- Conduct Data Protection Impact Assessments (DPIAs) for high-risk AI processing (Article 35)
- Implement data protection by design and by default (Article 25)
- Demonstrate that AI model training data, decision logic, and outputs comply with all six principles in Article 5(1)
- Keep audit logs sufficient to demonstrate compliance to supervisory authorities
- Appoint a Data Protection Officer (DPO) where large-scale processing of special category data is involved (Article 37)

**Key Accountability Documentation Required:**

| Document | Requirement |
|------------------------|-------------------------------------------------------|
| Processing Records | Article 30 — document all AI-related processing |
| DPIA | Article 35 — for high-risk AI processing activities |
| Consent Records | Article 7(1) — where consent is the lawful basis |
| Data Retention Policy | Article 5(1)(e) — maximum retention periods |
| Model Documentation | Evidence of accuracy and fairness assessments |

---

## Article 15 — Right of Access by the Data Subject

### Article 15(1): Right to Confirmation and Access

The data subject shall have the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information:

**(a)** The purposes of the processing

**(b)** The categories of personal data concerned

**(c)** The recipients or categories of recipient to whom the personal data have been or will be disclosed

**(d)** Where possible, the envisaged period for which the personal data will be stored, or, if not possible, the criteria used to determine that period

**(e)** The existence of the right to request from the controller rectification or erasure of personal data or restriction of processing of personal data concerning the data subject or to object to such processing

**(f)** The right to lodge a complaint with a supervisory authority

**(g)** Where the personal data are not collected from the data subject, any available information as to their source

**(h)** The existence of automated decision-making, including profiling, referred to in Article 22(1) and (4) and, at least in those cases, meaningful information about the logic involved, as well as the significance and the envisaged consequences of such processing for the data subject

### Article 15(2): Transfers to Third Countries

Where personal data are transferred to a third country or to an international organisation, the data subject shall have the right to be informed of the appropriate safeguards pursuant to Article 46 relating to the transfer.

### Article 15(3): Copy of Personal Data

The controller shall provide a copy of the personal data undergoing processing. For any further copies requested by the data subject, the controller may charge a reasonable fee based on administrative costs.

### Article 15(4): Rights of Others

The right to obtain a copy referred to in paragraph 3 shall not adversely affect the rights and freedoms of others.

**Implications for AI Systems:**

When an AI system processes personal data to make decisions, Article 15(1)(h) creates a specific obligation to explain:
- That automated decision-making exists
- **Meaningful information about the logic** used (model explainability requirement)
- The **significance** of those decisions for the individual
- The **envisaged consequences** of the AI processing

---

## Article 22 — Automated Individual Decision-Making, Including Profiling

### Article 22(1): General Prohibition on Solely Automated Decisions

The data subject shall have the right **not to be subject to a decision based solely on automated processing**, including profiling, which produces legal effects concerning him or her or similarly significantly affects him or her.

### Article 22(2): Exceptions to the General Prohibition

Paragraph 1 shall not apply if the decision:

**(a)** Is necessary for entering into, or performance of, a contract between the data subject and a data controller

**(b)** Is authorised by Union or Member State law to which the controller is subject and which also lays down suitable measures to safeguard the data subject's rights and freedoms and legitimate interests

**(c)** Is based on the data subject's explicit consent

### Article 22(3): Safeguards Where Exceptions Apply

In the cases referred to in points (a) and (c) of paragraph 2, the data controller shall implement suitable measures to safeguard the data subject's rights and freedoms and legitimate interests, at least the right to obtain **human intervention** on the part of the controller, to **express his or her point of view** and to **contest the decision**.

### Article 22(4): Special Category Data in Automated Decisions

Decisions referred to in paragraph 2 shall not be based on special categories of personal data referred to in Article 9(1), unless point (a) or (g) of Article 9(2) applies and suitable measures to safeguard the data subject's rights and freedoms and legitimate interests are in place.

**Key Rights Triggered by Article 22:**

| Right | Description |
|----------------------|-----------------------------------------------|
| Human Intervention | Right to request a human review the decision |
| Express View | Right to provide context or explanation |
| Contest Decision | Right to challenge and seek reversal |
| Explanation | Right to meaningful information about the logic |

**Practical AI Governance Requirements Under Article 22:**

- AI systems making consequential decisions must **not operate in a fully automated manner** without one of the Article 22(2) exceptions being satisfied
- Where exceptions apply, organisations must provide a **human review mechanism**
- Special category data (health, ethnicity, biometrics, etc.) cannot be used in automated decisions without explicit consent or substantial public interest
- Data Protection Impact Assessments are **mandatory** for systematic, large-scale automated decision-making (Article 35(3)(a))
- Profiling for marketing, credit, recruitment, or similar purposes requires clear lawful basis and opt-out mechanisms

---

## Summary: GDPR–AI Governance Compliance Checklist

| Article | Obligation | AI System Requirement |
|---------|-----------|----------------------|
| 5(1)(a) | Transparency | Explainable AI decisions |
| 5(1)(c) | Data minimisation | Train/use only necessary data |
| 5(1)(d) | Accuracy | Monitor and correct model drift |
| 5(2) | Accountability | Maintain audit logs and DPIAs |
| 15(1)(h) | Right of access to logic | Provide model explainability |
| 22(1) | No solely automated decisions | Require human oversight |
| 22(3) | Safeguards | Human review, contest, explain |
