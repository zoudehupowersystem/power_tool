# PowerTool Manual - Electromechanical Oscillation

## 1. Page objective
This page estimates the dominant electromechanical oscillation frequency from a simplified synchronizing-torque approximation. It is useful for teaching, order-of-magnitude checks, and preliminary parameter sensitivity studies.

## 2. Modeling boundary
The page assumes a reduced equivalent between internal emf, terminal voltage, and equivalent reactance. It is not a full modal-analysis platform and does not replace multi-machine eigenvalue studies.

## 3. Input suggestions
- Keep voltage, reactance, and operating power on a consistent per-unit base.
- Use a realistic inertia time constant, because it directly affects the natural frequency.
- Treat the result as an approximate dominant oscillation frequency rather than a complete damping assessment.

## 4. Workflow
1. Establish a reasonable operating point.
2. Run the page and note the initial angle, synchronizing coefficient, and frequency.
3. Vary `P0`, `XΣ`, or `T_j` one by one to observe the sensitivity.

## 5. Result interpretation
- Larger synchronizing torque generally pushes the oscillation frequency upward.
- Larger inertia lowers the oscillation frequency.
- If the estimated frequency conflicts with system experience, recheck the equivalent reactance and operating point first.

## 6. Troubleshooting checklist
- Inconsistent per-unit bases.
- Unrealistic operating power close to the static limit.
- Using the approximation as if it were a full damping or participation-factor study.

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
