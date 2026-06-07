# Indie Game Idea Graph Design Spec

## 1. Purpose

This document describes a modular product design for an indie game idea discovery system. The system helps independent game developers move from vague interest and limited resources to a small set of explainable, comparable, and prototype-ready game concepts.

This is not an implementation plan. It does not prescribe database products, frameworks, model providers, UI architecture, or deployment choices. It defines the story, system boundaries, module responsibilities, data contracts, and independent acceptance criteria.

## 2. Product Thesis

Independent developers often do not need more random ideas. They need ideas that fit their constraints, connect to real game design patterns, differ meaningfully from references, and can be tested through small prototypes.

The system should act like a design-aware production advisor:

1. It studies selected games as design examples.
2. It extracts reusable design knowledge from those games.
3. It understands the developer's constraints and interests.
4. It finds suitable opportunity areas.
5. It forms bounded opportunity frames.
6. It turns those frames into concrete concept cards.
7. It identifies what each concept must prove in a prototype.

The system must not promise that a generated concept will be fun or commercially successful. Its value is reducing ambiguity before development begins.

## 3. Scope

### In Scope

- Curated seed games, selected for design relevance rather than volume.
- Structured game design profiles for each seed game.
- AI-assisted but human-reviewed design annotation.
- A design knowledge graph made of games, mechanics, player experiences, production constraints, innovation patterns, and reusable reference patterns.
- Developer profiles containing constraints, preferences, and interests.
- Opportunity frames that explain why a design area fits a developer.
- Concept cards generated only from bounded opportunity frames.
- Concept comparison across safety, fit, novelty, and risk.
- Prototype validation briefs that state specific testable hypotheses.

### Out of Scope For The First Version

- Feedback loops that automatically update the graph after user reactions.
- Full Steam-scale game indexing.
- Claims that the system can predict fun or market success.
- Fully automatic admission of AI-generated annotations into the trusted graph.
- Long-term production planning, task estimation, staffing, budgeting, or release planning.

## 4. Core Workflow

```text
Curated Game Intake
-> Game Design Annotation
-> Human Review
-> Design Knowledge Graph
-> Developer Profile
-> Opportunity Matching
-> Opportunity Frame
-> Concept Generation
-> Concept Evaluation
-> Prototype Validation Brief
```

The most important boundary is between Opportunity Frame and Concept Generation. The system should not ask a language model to invent freely from a broad prompt. It should first assemble a constrained frame from known game design evidence, then use generation only to make that frame concrete and readable.

## 5. System Artifacts

These artifacts are the stable handoffs between modules.

### 5.1 Game Candidate

A game selected for possible inclusion.

Required fields:

- Title
- Source reference
- Short description
- Selection rationale
- Relevance category

Relevance categories may include:

- Mechanically distinctive
- Solo-friendly reference
- Low-production-cost reference
- High-system-depth reference
- Strong innovation pattern
- Representative genre example

### 5.2 Game Design Profile

A structured interpretation of one game.

Required fields:

- One-sentence design summary
- Core loop
- Main player actions
- Main player decisions
- Primary player experiences
- Main mechanics
- Progression model
- Failure model
- Replayability source
- Content structure
- Production constraints
- Innovation patterns
- Reusable reference patterns
- Non-copyable risks
- Evidence notes
- Confidence level
- Review status

### 5.3 Design Claim

A single reviewable statement about a game or design pattern.

Examples:

- "Balatro uses familiar poker rules to reduce learning cost."
- "Into the Breach creates high tactical depth through small-board perfect information."
- "Abstract card UI can reduce animation burden for solo developers."

Required fields:

- Subject
- Relation
- Object
- Explanation
- Evidence
- Confidence
- Review status

### 5.4 Developer Profile

A structured description of the developer's reality and preferences.

Required fields:

- Team size
- Development time budget
- Programming strength
- Art strength
- Audio strength
- Content production capacity
- Preferred game references
- Disliked game references or mechanics
- Desired player experience
- Hard constraints
- Strong preferences
- Soft preferences

Constraint types:

- Hard constraints: must not be violated.
- Strong preferences: should be respected unless a concept has exceptional upside.
- Soft preferences: can be traded off for novelty or fit.

### 5.5 Opportunity Frame

A bounded creative brief assembled before concept generation.

Required fields:

- Target developer profile summary
- Matched opportunity area
- Source games
- Relevant mechanics
- Relevant player experiences
- Relevant production constraints
- Relevant innovation patterns
- Recommended transformations
- Prohibited directions
- Evidence paths
- Fit rationale
- Risk rationale

The Opportunity Frame is the system's main defense against unconstrained idea generation.

### 5.6 Concept Card

A concrete game idea derived from one Opportunity Frame.

Required fields:

- Title
- One-sentence concept
- Core fantasy
- Core loop
- Main player decisions
- Main mechanics
- Reference sources
- Difference from references
- Why it fits the developer
- Production risk
- Design risk
- Novelty rationale
- Suggested prototype scope

### 5.7 Concept Evaluation

A structured comparison of concept cards.

Required fields:

- Fit score
- Feasibility score
- Novelty score
- Risk score
- Evidence quality score
- Classification

Classifications:

- Safe: highly feasible, lower novelty.
- Balanced: meaningful novelty with manageable risk.
- Stretch: stronger novelty, clear capability challenge.

### 5.8 Prototype Validation Brief

A focused statement of what the first prototype must test.

Required fields:

- Riskiest assumption
- Minimum prototype contents
- Target play session length
- Success signals
- Failure signals
- What not to build yet

The brief must avoid generic statements such as "verify whether the game is fun." It should name observable behaviors or design properties.

## 6. Modules

Each module must be independently testable through its input and output artifacts. No module should require a full end-to-end system run to validate its basic behavior.

### 6.1 Curated Game Intake Module

Purpose:

Select and register candidate games for the seed library.

Inputs:

- Game title or store link
- Optional curator note
- Optional reference category

Outputs:

- Game Candidate

Responsibilities:

- Record why the game belongs in the seed library.
- Reject games that are only famous but not useful as design references.
- Prefer games with clear mechanics, clear constraints, or strong innovation patterns.

Must Not:

- Decide final design annotations.
- Infer full mechanics or innovation patterns.
- Admit a game into the trusted graph without later review.

Independent Test Cases:

- Given a mechanically distinctive indie game, the module creates a Game Candidate with a clear selection rationale.
- Given a game with insufficient relevance, the module marks it as low priority or rejects it.
- Given only a store link, the module still produces a minimal candidate record with missing fields explicitly marked.

Acceptance Criteria:

- Every accepted candidate has a stated reason for inclusion.
- Every candidate can be traced to at least one source reference.
- No candidate is treated as trusted design knowledge at this stage.

### 6.2 Game Design Annotation Module

Purpose:

Produce a structured draft interpretation of a game as a design object.

Inputs:

- Game Candidate
- Source material
- Optional curator notes

Outputs:

- Draft Game Design Profile
- Draft Design Claims

Responsibilities:

- Identify core loop, player actions, decisions, experiences, mechanics, innovation patterns, and production constraints.
- Separate observed facts from interpretive claims.
- Attach evidence and confidence to important claims.
- Surface uncertainty rather than hiding it.

Must Not:

- Mark its own output as trusted.
- Convert vague claims into graph facts without review.
- Overwrite human-reviewed annotations.

Independent Test Cases:

- Given a known game with strong source material, the module produces a complete draft profile.
- Given weak source material, the module marks confidence as low and identifies missing evidence.
- Given conflicting source material, the module preserves uncertainty instead of choosing silently.

Acceptance Criteria:

- Each draft profile includes core loop, mechanics, experiences, constraints, and innovation notes.
- Each non-obvious claim includes evidence or an explicit uncertainty marker.
- Draft output is clearly distinguishable from reviewed output.

### 6.3 Human Review Module

Purpose:

Turn draft annotations into trusted design knowledge.

Inputs:

- Draft Game Design Profile
- Draft Design Claims
- Reviewer edits

Outputs:

- Reviewed Game Design Profile
- Approved, revised, or rejected Design Claims

Responsibilities:

- Confirm or correct high-impact design claims.
- Standardize terminology across games.
- Prevent noisy or speculative annotations from entering the trusted graph.
- Preserve reviewer notes for future interpretation.

Must Not:

- Generate new concepts.
- Change developer profile constraints.
- Automatically approve low-confidence claims.

Independent Test Cases:

- Given a draft with unsupported claims, the module can reject or downgrade those claims.
- Given two similar mechanics with inconsistent naming, the module can normalize them.
- Given reviewer edits, the module preserves the reason for changes.

Acceptance Criteria:

- No trusted claim lacks review status.
- Rejected claims remain auditable but are not used for recommendation.
- Important terminology is normalized before graph admission.

### 6.4 Design Knowledge Graph Module

Purpose:

Maintain reviewed design knowledge as connected concepts.

Inputs:

- Reviewed Game Design Profiles
- Approved Design Claims

Outputs:

- Queryable design relationships
- Evidence paths
- Candidate opportunity subgraphs

Responsibilities:

- Connect games to mechanics, experiences, constraints, styles, genres, themes, innovation patterns, and reusable reference patterns.
- Preserve evidence and confidence on relationships.
- Support traversal from developer constraints to relevant games and design patterns.
- Support comparison between similar and contrasting games.

Must Not:

- Invent new claims without reviewed input.
- Generate final concept cards.
- Treat popularity as equivalent to design relevance.

Independent Test Cases:

- Given approved claims for a game, the module exposes the expected relationships.
- Given a target constraint such as low art cost, the module returns related games, mechanics, and patterns.
- Given a game, the module returns evidence-backed paths explaining why it matches a design pattern.

Acceptance Criteria:

- Every relationship used downstream can be traced back to an approved or explicitly draft-level claim.
- The module can return both direct matches and multi-step evidence paths.
- The module can distinguish strong evidence from weak evidence.

### 6.5 Developer Profile Module

Purpose:

Represent the user's capabilities, constraints, and interests in a form the rest of the system can use.

Inputs:

- User answers
- Favorite games
- Disliked games or mechanics
- Desired project scale

Outputs:

- Developer Profile

Responsibilities:

- Convert free-form user input into structured constraints and preferences.
- Separate hard constraints from strong and soft preferences.
- Identify missing profile information.
- Preserve the user's stated language and intent.

Must Not:

- Recommend games or concepts.
- Treat all preferences as hard filters.
- Silently infer critical constraints without asking or marking uncertainty.

Independent Test Cases:

- Given a solo developer with weak art ability, the module captures low art capacity as a strong preference or hard constraint according to user wording.
- Given ambiguous time budget, the module marks the profile as incomplete.
- Given favorite games, the module extracts interests without assuming the user wants to copy them.

Acceptance Criteria:

- Every profile distinguishes hard constraints, strong preferences, and soft preferences.
- Missing critical information is visible.
- The profile can be used without reading the original conversation.

### 6.6 Opportunity Matching Module

Purpose:

Find promising regions of the design graph that fit the developer profile.

Inputs:

- Developer Profile
- Design Knowledge Graph outputs

Outputs:

- Candidate opportunity areas

Responsibilities:

- Use developer constraints and preferences as scoring modifiers.
- Respect hard constraints.
- Avoid reducing all recommendations to the safest familiar patterns.
- Surface safe, balanced, and stretch opportunity areas.

Must Not:

- Produce final concepts.
- Apply every preference as a hard filter.
- Hide trade-offs between fit and novelty.

Independent Test Cases:

- Given strict hard constraints, the module excludes incompatible areas.
- Given strong but non-hard preferences, the module can still return a stretch option with warnings.
- Given a sparse match, the module explains which constraints narrowed the result.

Acceptance Criteria:

- Every opportunity area includes a fit rationale and constraint trade-off.
- Results include more than one risk posture when possible.
- The module can explain why an attractive area was rejected.

### 6.7 Opportunity Framing Module

Purpose:

Create a bounded creative brief that connects evidence to possible concept generation.

Inputs:

- Candidate opportunity area
- Evidence paths
- Developer Profile

Outputs:

- Opportunity Frame

Responsibilities:

- Assemble the source games, mechanics, experiences, constraints, and innovation patterns behind an opportunity.
- Define recommended transformations such as combination, inversion, migration, compression, or substitution.
- Define prohibited directions based on hard constraints and high-risk mismatches.
- Make the reasoning explicit enough that a human can challenge it.

Must Not:

- Write polished final concepts.
- Introduce unsupported mechanics or references.
- Omit risk rationale.

Independent Test Cases:

- Given a low-art, high-replayability opportunity, the module produces a frame with matching evidence paths.
- Given a hard constraint against multiplayer, the frame prohibits multiplayer-dependent concepts.
- Given weak evidence, the frame marks the opportunity as low-confidence.

Acceptance Criteria:

- Every frame cites source games or reviewed design claims.
- Every frame includes both allowed transformations and prohibited directions.
- Every frame can be read as a standalone creative brief.

### 6.8 Concept Generation Module

Purpose:

Turn Opportunity Frames into concrete, readable game concepts.

Inputs:

- Opportunity Frame

Outputs:

- Concept Cards

Responsibilities:

- Generate multiple concepts within the frame's allowed design space.
- Make each concept specific enough to evaluate.
- Preserve references, constraints, and transformation logic.
- Avoid concepts that violate prohibited directions.

Must Not:

- Invent unsupported rationale.
- Ignore developer constraints.
- Claim the concept will be fun or successful.

Independent Test Cases:

- Given an Opportunity Frame with clear prohibited directions, generated concepts avoid them.
- Given the same frame, generated concepts differ meaningfully rather than rewording one idea.
- Given a frame with weak evidence, generated concepts carry appropriate uncertainty.

Acceptance Criteria:

- Every Concept Card maps back to one Opportunity Frame.
- Every Concept Card states references and differences from references.
- Every Concept Card includes both production and design risks.

### 6.9 Concept Evaluation Module

Purpose:

Compare generated concepts in a way that helps the developer choose.

Inputs:

- Concept Cards
- Developer Profile
- Opportunity Frame

Outputs:

- Concept Evaluations
- Ranked concept set

Responsibilities:

- Score fit, feasibility, novelty, risk, and evidence quality.
- Classify concepts as safe, balanced, or stretch.
- Explain scoring trade-offs.
- Highlight when a concept is attractive but misaligned with the developer's current limits.

Must Not:

- Treat the highest novelty concept as automatically best.
- Hide uncertainty behind a numeric score.
- Remove stretch concepts solely because they are risky, unless they violate hard constraints.

Independent Test Cases:

- Given a safe but familiar concept and a risky novel concept, the module distinguishes their trade-offs.
- Given a concept that violates a hard constraint, the module rejects or flags it.
- Given low evidence quality, the module lowers confidence even if the idea sounds appealing.

Acceptance Criteria:

- Each score includes a short explanation.
- Each concept receives one of the defined classifications.
- The ranking helps comparison but does not pretend to be an objective success prediction.

### 6.10 Prototype Validation Module

Purpose:

Translate a concept's biggest uncertainty into a minimal test.

Inputs:

- Concept Card
- Concept Evaluation

Outputs:

- Prototype Validation Brief

Responsibilities:

- Identify the riskiest assumption.
- Define a minimum prototype scope.
- Define observable success and failure signals.
- Explicitly list what should not be built yet.

Must Not:

- Use generic validation advice.
- Expand the idea into a full production plan.
- Require assets or systems unnecessary for the first test.

Independent Test Cases:

- Given a concept based on rule manipulation, the module tests whether players understand and exploit rule changes.
- Given a concept with low-art constraints, the module tests whether feedback works without polished art.
- Given a concept with replayability claims, the module tests whether early variation creates replay intent.

Acceptance Criteria:

- Each brief names one primary riskiest assumption.
- Each brief can be acted on without a full game plan.
- Each brief includes concrete success and failure signals.

### 6.11 Audit And Explanation Module

Purpose:

Make the system's reasoning inspectable.

Inputs:

- Game Design Profiles
- Design Claims
- Opportunity Frames
- Concept Cards
- Concept Evaluations
- Prototype Validation Briefs

Outputs:

- Explanation trail
- Source references
- Claim lineage

Responsibilities:

- Show how a concept was derived from source games, claims, and developer constraints.
- Distinguish reviewed knowledge from draft knowledge.
- Make weak or speculative reasoning visible.
- Support human review of suspicious recommendations.

Must Not:

- Rewrite the recommendation itself.
- Hide missing evidence.
- Present draft claims as approved facts.

Independent Test Cases:

- Given a Concept Card, the module returns the source Opportunity Frame and supporting claims.
- Given a questionable claim, the module shows review status and confidence.
- Given a rejected claim, the module verifies it was not used as trusted evidence.

Acceptance Criteria:

- Every final recommendation has an explanation trail.
- The explanation trail can identify unsupported or low-confidence links.
- A human reviewer can inspect why the system recommended a concept.

## 7. Cross-Module Rules

### 7.1 Evidence Before Generation

Concept generation must be downstream of an Opportunity Frame. The system must not produce final concepts directly from a developer profile alone.

### 7.2 Human Review Before Trust

AI-generated design claims may be useful drafts, but they are not trusted graph knowledge until reviewed.

### 7.3 Constraints Are Weighted, Not Flattened

The system must distinguish hard constraints from strong and soft preferences. Hard constraints block concepts. Strong and soft preferences affect scoring and risk warnings.

### 7.4 No Claim Of Fun

The system may estimate fit, feasibility, novelty, and risk. It must not claim that a concept is fun before prototyping.

### 7.5 Explainability Is A Product Feature

Every recommendation must be explainable through source games, design claims, developer constraints, and transformation logic.

## 8. End-To-End Example

Developer profile:

- Solo developer
- Strong programming ability
- Weak art ability
- Three-month prototype goal
- Likes systemic strategy, short sessions, and replayability
- Likes games such as Balatro and Into the Breach
- Does not want long narrative content or online multiplayer

Opportunity area:

- Low art cost
- Short sessions
- High replayability
- Systemic depth
- Symbolic or board-like presentation

Opportunity Frame:

- Source games: Balatro, Into the Breach, Baba Is You
- Relevant mechanics: rule modification, compact tactical space, familiar rule literacy
- Relevant experiences: combo satisfaction, tactical foresight, emergent problem solving
- Recommended transformations: compress space, substitute animation with symbolic feedback, combine rule editing with short tactical runs
- Prohibited directions: online multiplayer, large maps, long scripted story, animation-heavy combat

Concept Card:

- Title: Ruleforge Tactics
- One-sentence concept: A short-session tactical game where the player wins by editing the rules of a tiny battlefield rather than directly commanding units.
- Difference from references: It borrows compact tactical pressure and rule manipulation, but frames each run as a build of temporary battlefield laws.
- Fit rationale: It favors systems over art volume, supports short prototypes, and can start with simple symbolic presentation.
- Main risk: Players may not understand rule consequences quickly enough.

Prototype Validation Brief:

- Riskiest assumption: Players can understand and enjoy changing battlefield rules within the first few minutes.
- Minimum prototype: One 4x4 board, three unit types, six rule cards, five encounters.
- Success signal: Test players can explain rule consequences after one run and voluntarily replay to try a different rule combination.
- Failure signal: Players treat outcomes as arbitrary or cannot predict what their rule changes will do.
- Do not build yet: Campaign progression, polished art, large content sets, meta-progression, online features.

## 9. Validation Strategy

The system should be validated at three levels.

### 9.1 Module-Level Validation

Each module must pass fixture-based tests against known input artifacts. Exact wording may vary for generated text, but required fields, prohibited behavior, evidence use, and constraint handling must be testable.

### 9.2 Flow-Level Validation

The full flow should be tested with several developer profiles:

- Solo programmer with weak art ability.
- Designer-heavy team with weak programming ability.
- Small team seeking high novelty.
- Developer with strict genre dislikes.
- Developer with very limited time.

Each profile should produce opportunity frames, concept cards, evaluations, and validation briefs that reflect its constraints.

### 9.3 Human Judgment Review

Domain reviewers should inspect:

- Whether game profiles are accurate.
- Whether opportunity frames are genuinely evidence-backed.
- Whether concepts are meaningfully different from references.
- Whether prototype briefs are specific enough to act on.

## 10. Success Criteria

The product succeeds if:

- A user can understand why each concept was recommended.
- Concepts reflect the user's constraints without becoming overly conservative.
- The system produces specific prototype validation briefs rather than generic advice.
- Reviewed design knowledge improves recommendation quality.
- The workflow turns vague creative uncertainty into comparable project candidates.

The product fails if:

- It behaves like a tag search engine.
- It generates concepts directly from broad prompts without evidence.
- It relies on unreviewed AI claims as trusted knowledge.
- It repeatedly recommends only obvious low-risk clones.
- Its prototype advice is too generic to guide action.

## 11. Open Questions For Review

1. What is the first target size of the curated seed library: 50, 75, or 100 games?
2. Who is allowed to approve design claims in the first version?
3. How strict should the system be when a stretch concept challenges the developer's stated limits?
4. Which game genres should be intentionally overrepresented in the seed library because they are more useful to indie developers?
5. What level of evidence is required before an innovation pattern becomes reusable across games?

