# Aegis-APAC: Rules for AI Coding Agents

Follow these hard rules on every coding task without exception:

1. **Numbers come from code, never from Gemini.**
   - Depths, timings, geometry, and infrastructure graph traversals are strictly deterministic.
   - Gemini drafts role-specific text, translates, reads storm bulletins, analyses citizen photos, and performs read-only visual QA. It never produces or overrides ground-truth numerical values.

2. **Every advisory is validated.**
   - Every number, timestamp, facility name, and road name in an advisory must exist in the input decision JSON.
   - If validation fails, immediately reject and fall back to the safe deterministic template.

3. **Probabilities, not single deterministic lines.**
   - Hazard outputs are ensemble-based (30–50 perturbed members).
   - The UI and API must always communicate risk as probabilities (e.g. $P(\text{depth} > 0.3\text{m})$) and earliest exceedance time, never a single unqualified prediction.

4. **Assumptions are explicitly labelled.**
   - Every inferred infrastructure dependency, default failure threshold, and backup runtime must include `assumption: true` in the data payload and display an assumption badge in the UI.

5. **Human approval required before dispatch.**
   - Advisories transition from `draft` -> `approved` -> `dispatched`.
   - No alert may be marked dispatched without explicit operator confirmation.

6. **Precompute, then serve.**
   - Earth Engine runs exclusively in offline/batch jobs.
   - The web application and API must never call Earth Engine directly per user request. The demo runs entirely from the frozen `data/golden/` bundle when `DEMO_MODE=true`.

7. **Configuration over hard-coding.**
   - Thresholds, bounding boxes, perturbation ranges, and region settings live in `regions/<name>/config.yaml`.

8. **Never invent facts or dataset IDs.**
   - Verify dataset identifiers, model versions, and library APIs against official documentation.
