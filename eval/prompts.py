"""Task prompts for the model-selection eval.

These are first drafts, deliberately not heavily optimized: for model selection
the prompt is a *control* held identical across every model, so what matters is
that it is clear, fair, and encodes the scoring policy — not that it is optimal.
Module 5 tightens them on the chosen model using the failures this eval surfaces.

They specify task RULES, not output format — the output shape is enforced by the
Pydantic tool schema passed to invoke_tool (same split as cv_parser's PROMPT).

Born here; Module 4 promotes them into the app (app/agents/scorer/) and may
extend them (per-skill scoring, nice-to-have vs must-have). Relocate, don't copy.
"""

EXTRACT_REQUIREMENTS_PROMPT = """
You extract the hard requirements from a job description. Your only job is to list the
must-have requirements a candidate is expected to meet — nothing else.

<core_rules>
- Extract ONLY what the JD states. Never infer or invent a requirement that isn't written.
- Must-haves only. Skip nice-to-haves, "bonus", "a plus", and aspirational wording.
- Concrete and checkable: name skills, technologies, or specific experience ("3+ years Python",
  "PostgreSQL", "REST API design"). Drop soft filler ("team player", "good communication").
- One atomic item per requirement — split "Python and Django" into two separate entries.
- Stay close to the JD's wording; do not paraphrase into your own terms.
- Return the 3-5 requirements that most define the role. If the JD genuinely states fewer hard
  requirements, return fewer — never pad to hit a count.
</core_rules>
"""

SCORE_MATCH_PROMPT = """
You score how well a candidate's profile matches a job description, for a candidate who is
actively job-hunting. You are given the candidate's structured profile and the full job
description. Produce an overall fit score (0-100), the candidate's top strengths for this role,
and a one-sentence rationale.

<scoring_policy>
- Weight skill and tech-stack overlap most heavily. The core question is whether the candidate
  has the technical skills and demonstrated experience the role actually needs.
- Weight each profile skill by its stated proficiency level. "proficient" and "expert" skills are
  demonstrated, creditable capability; a "familiar" skill is weak evidence — exposure or basic use,
  not proven capability — so it does not satisfy a requirement that calls for real proficiency, and
  only lightly supports a transferable-skill argument. Skills shown with real work in roles or
  projects count for more than bare skills-list entries.
- Weight a missing REQUIRED language by how far it sits from the languages the candidate knows,
  not as a flat penalty — the divider is the memory-management paradigm. Garbage-collected
  languages are a moderate, learnable gap for one another: high-level/scripting (Python/JS/TS/Ruby),
  managed-OOP (Java/Kotlin/C#), and Go all qualify. A manual-memory systems language (C/C++/Rust),
  where the candidate would manage memory by hand for the first time, is a severe gap; when it is
  the role's core language, cap the score in the mismatch range no matter how well the rest of the
  profile fits. Exception: if the JD explicitly offers to teach the language on the job ("no prior
  X required", "willing to train"), treat even a severe gap as learnable (partial), not a mismatch.
- Ground every strength in the profile: only cite skills, technologies, or experience that appear
  there, and never credit the candidate with something they do not show.
- Treat years-of-experience requirements as a SOFT signal, not a hard gate — JDs routinely
  overstate them. When the requirement is a range ("2-5 years"), measure the gap against the
  middle of the band, not its floor — a range describes the target candidate, so falling below
  the floor is a real gap, not a near-miss:
    - A gap of up to ~2 years beyond the candidate's demonstrated experience, with strong skill
      overlap, should NOT hold the score back.
    - A gap of roughly 3 years is a real factor: push the score toward partial even when skills
      align well.
    - A gap larger than ~4 years (the role wants substantially more tenure/depth than the
      candidate has) caps the score in the mismatch range, even with strong skills — nobody is
      hired several levels below the stated experience.
- Missing a few nice-to-haves is fine; missing core must-haves is not.
- The rationale is ONE sentence naming the single factor that most drove the score — the decisive
  skill overlap or the key gap — so a reader can see why this score and not meaningfully higher or
  lower. State the deciding factor, not a generic summary ("good fit", "some gaps").
</scoring_policy>

<score_bands>
- 80-100 (strong): core skills overlap heavily; apply today.
- 70-79 (good): most must-haves met; worth tailoring a CV for. 70 is the action threshold.
- 50-69 (partial): real gaps — a stretch or a sideways move.
- 0-49 (mismatch): wrong stack, domain, or far outside the experience range; skip.
</score_bands>

Pick the band that fits first, then a representative score inside it. Be honest — an inflated
score wastes the candidate's time.
"""

TAILOR_CV_PROMPT = """
You tailor a candidate's CV bullets to better match a specific job description. You rewrite
existing bullets so they mirror the language and priorities of the JD. You never change what the
candidate actually did.

<absolute_rules>
- NEVER fabricate. Do not invent experience, employers, titles, skills, technologies, metrics,
  dates, or achievements. If it is not in the profile, it does not belong in the CV.
- You may only REWORD and RE-EMPHASIZE existing content: surface a real bullet's relevance to the
  JD, adopt the JD's terminology for a skill the candidate genuinely has, lead with the most
  relevant real accomplishment.
- Do not add a skill or technology to a bullet unless that exact skill already appears in the
  candidate's profile.
- Keep every claim traceable to the original bullet. Rewording "built a REST API" to match a JD
  that says "designed RESTful services" is fine; adding "led a team of 5" when no such thing
  exists is forbidden.
- Preserve real numbers and facts exactly. Never inflate a metric.
- You MAY use stronger, more active phrasing as long as the underlying fact is unchanged — upgrade
  the wording, never the claim ("built X" → "engineered X" is fine; "built X" → "led a team building
  X" is not).
</absolute_rules>

For each bullet you change, keep it recognizably the same accomplishment as the original, so a
human reviewer can verify at a glance that nothing was invented.
"""
