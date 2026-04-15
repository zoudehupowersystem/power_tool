# PowerTool Manual - Transient Stability Assessment

## 1. Function
This page combines the impact method and the equal-area criterion for quick transient-stability assessment in a classical single-machine infinite-bus setting.

## 2. When to use it
Use the page when you need a fast view of fault severity, critical clearing margin, and first-swing stability. It is suitable for conceptual studies and early-stage screening.

## 3. Impact-method workflow
1. Enter the disturbance acceleration power, clearing time, and oscillation frequency.
2. Run the impact method to obtain a quick estimate of the power-angle swing amplitude.
3. Use the result as a first sanity check before performing the equal-area calculation.

## 4. Equal-area workflow
1. Enter mechanical power together with pre-fault, fault, and post-fault `Pmax` values.
2. Run the calculation and examine the key angles, accelerating area, and decelerating area.
3. Compare the actual clearing time with the critical clearing time.

## 5. Important cautions
- The classical model neglects damping and assumes constant mechanical power.
- The equal-area criterion is a first-swing criterion and does not represent multi-swing behavior.
- If the actual network changes significantly after the fault, verify the result with a formal transient-stability program.

## 6. Recommendation
Use this page to identify clearly safe or clearly unsafe cases quickly, then move marginal cases to detailed simulation.

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
