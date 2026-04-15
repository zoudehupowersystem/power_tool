# PowerTool Manual - Voltage / Reactive Power Analysis: Line Natural Power and Reactive Power

## 1. Functional positioning
This page estimates line surge impedance, natural power, and the sign of the line reactive-power balance. It is intended for EHV and UHV long-line intuition building and quick checks.

## 2. Input explanation
- Enter the rated line voltage and either the surge impedance directly or the per-unit-length inductance and capacitance.
- Enter the actual transmitted active power, the charging reactive power per unit length, and the line length.
- Use the page near rated voltage unless you are prepared to correct charging reactive power with the voltage-squared factor.

## 3. Operating steps
1. Fill in the line data and operating power.
2. Run the page and review `Z_c`, `P_N`, and `ΔQ_L`.
3. Compare the actual power with the natural power to judge whether the line tends to generate or absorb reactive power.

## 4. Reading the result
- If transmitted active power is lower than natural power, the line usually behaves as net capacitive.
- If transmitted active power is above natural power, net inductive behavior becomes more likely.
- The page result is strongest when the line is close to its rated-voltage operating condition and does not have complicated compensation devices.

## 5. Common issues
- Mixing the direct surge-impedance input with inconsistent `L` and `C` assumptions.
- Treating the result as exact when the operating voltage deviates strongly from the rated value.
- Forgetting that complex series/shunt compensation changes the reactive-power picture.

## 6. Recommendation
Use the page as a first-pass reactive-balance estimate for long lines, then confirm important cases with detailed network studies.

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
