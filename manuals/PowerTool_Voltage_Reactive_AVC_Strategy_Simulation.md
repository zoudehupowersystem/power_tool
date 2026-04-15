# PowerTool Manual - Voltage / Reactive Power Analysis: AVC Strategy Simulation

## 1. Page objective
This page applies a simplified nine-zone AVC strategy to recommend tap changes and reactive-compensation actions. It is intended for operational screening and teaching demonstrations.

## 2. Meaning of the main parameters
- High-side and low-side voltages define the present operating point.
- Tap limits, current tap position, and tap-step percentage describe the controllable transformer range.
- Capacitor and reactor group settings define the available reactive-compensation actions.
- Power flow, system short-circuit level, and transformer parameters affect the estimated voltage response.

## 3. Recommended workflow
1. Enter the current operating point and the controllable equipment data.
2. Run the page and observe the current zone and the recommended action.
3. Check the estimated post-control state and compare it with the operating target band.
4. Repeat for several representative load conditions.

## 4. Key points in result interpretation
- The current zone identifies whether the issue is mainly voltage, reactive power, or both.
- The suggested tap and compensation actions are rule-based first-pass recommendations.
- The page includes a more accurate post-action estimate, but it is still an approximation rather than a full power-flow solution.

## 5. Common questions
- If the recommendation oscillates between actions, recheck the target band and the compensation step size.
- If the result looks too optimistic, verify the transformer short-circuit voltage and the system short-circuit level.

## 6. Implementation advice
Use the page to screen AVC strategies before they are turned into dispatch or station-control policies.

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
