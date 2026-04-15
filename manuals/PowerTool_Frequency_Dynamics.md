# PowerTool Manual - Frequency Dynamics

## 1. Purpose and applicability
Use this page for a quick estimate of post-disturbance frequency response. The main outputs are the frequency nadir, recovery speed, steady-state deviation, and the effect of primary control and optional AGC.

## 2. Input guidance
- `f0`: rated system frequency, typically 50 Hz.
- `ΔP_OL0`: initial active-power deficit in pu.
- `T_s`: equivalent inertia time constant. Larger values mean stronger inertial support.
- `T_G`: primary-control time constant. Smaller values mean a faster governor response.
- `k_D`: load-frequency damping coefficient.
- `k_G`: primary-frequency-response gain.
- Plot duration should be long enough to capture the dip, rebound, and settling process.

## 3. Recommended workflow
1. Run the default case once to understand the curve shape.
2. Keep `ΔP_OL0` fixed and vary `T_s`, `T_G`, and `k_G` to compare nadir and recovery time.
3. Enable AGC only after the basic primary-response trend is understood.
4. Record a simple input-versus-result table for later comparison.

## 4. How to interpret the result
- A low nadir usually points to insufficient inertia or slow primary response.
- A slow recovery often indicates weak primary gain or insufficient AGC action.
- A large steady-state deviation suggests that the static control gain or the load damping is too small.

## 5. Common pitfalls
- Extremely large `ΔP_OL0` or unrealistically small time constants can produce misleading shapes.
- Check the unit system carefully when comparing with field events.
- Remember that this is a reduced-order engineering model, not a whole-grid electromechanical-transient simulation.

## 6. Practical recommendation
Use this page to screen options quickly before detailed grid-level dynamic simulation.

## Appendix A: Input checklist
- Confirm that the voltage base, capacity base, and unit system are consistent.
- Check the dimensions of all key quantities before interpreting the result.
- Record the source of critical equipment data, such as nameplate values, test reports, or dispatch ledgers.
- Compare at least three representative operating conditions whenever the conclusion may affect operation.

## Appendix B: Turning results into action
1. Use the page result as a first-pass engineering screening tool.
2. For feasible options, prepare at least three boundary-condition check cases.
3. Review the key conclusions jointly with operation, protection, and maintenance staff when relevant.
4. Convert the result into an action sheet with trigger conditions, execution steps, rollback conditions, and alarm thresholds.

## Appendix C: FAQ
- **Why can the page result differ from field records?**  
  This software is an engineering approximation tool. It does not model every topology detail, controller dead band, or protection logic.
- **How can I improve confidence in the result?**  
  Improve input quality first, then compare multiple operating conditions and verify that the conclusion is stable.
- **When must I switch to a formal simulation platform?**  
  Move to formal simulation when the decision affects relay settings, plant commissioning, major operating-mode changes, or a narrow security margin.

## Appendix D: Suggested case-record template
| Item | Suggested content |
|---|---|
| Case name | For example, summer evening peak load or N-1 transformer mode |
| Key inputs | Voltage, power flow, equipment capacity, equivalent parameters |
| Page conclusion | Stability assessment, operating-zone assessment, or risk level |
| Suggested action | Tap change, compensation switching, operating-mode adjustment |
| Follow-up conclusion | Whether formal load-flow, transient-stability, or EMT studies are required |

## Appendix E: Delivery notes
- When exporting to operators, include the applicability limits and the prohibited conditions.
- When exporting to commissioning or test staff, include the parameter-source table and the software version.
- When exporting to managers, include the risk level, the implementation cost, and the recommended next step.
- Keep screenshots and text results after each use for later review.
