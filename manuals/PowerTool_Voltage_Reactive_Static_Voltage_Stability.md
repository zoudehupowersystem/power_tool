# PowerTool Manual - Voltage / Reactive Power Analysis: Static Voltage Stability

## 1. Page purpose
This page provides a quick static-voltage-stability estimate for a two-bus equivalent. It highlights the maximum transferable active power and the corresponding receiving-end minimum voltage.

## 2. Preparation before input
- Use a consistent per-unit base for voltage, impedance, and power.
- Check that the sending-end voltage can reasonably be treated as stiff.
- Use a representative load power factor; the approximation assumes it is approximately constant.

## 3. Recommended operating steps
1. Enter the sending-end voltage, equivalent reactance, power factor, and base capacity.
2. Run the calculation and note `P_L,max`, `V_min/U_g`, and the physical-unit conversion.
3. Compare the result with the current or target operating point.

## 4. Interpreting the result
- A lower voltage-stability limit often points to a larger equivalent reactance or a poorer load power factor.
- The minimum receiving-end voltage helps judge how narrow the voltage margin has become.
- The physical-unit conversion is useful when discussing the result with operating staff.

## 5. Common misconceptions
- The page is not a substitute for a full load-flow or continuation-power-flow study.
- Significant resistance, tap-changing action, or complicated reactive compensation can invalidate the approximation.

## 6. Engineering recommendation
Use this page for early-stage screening. If the margin is small or the operating condition is important, move to a formal power-flow and voltage-stability workflow.

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
