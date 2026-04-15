# PowerTool Manual - Parameter Validation & Per-Unit: Overhead Line

## 1. Purpose
This page converts named overhead-line parameters into per-unit values and checks whether the inputs lie in typical engineering ranges.

## 2. Suggested workflow
1. Enter the system base values, line length, and the positive- and zero-sequence parameters.
2. Run the calculation and review both the physical-unit summary and the per-unit summary.
3. If needed, open the line-geometry calculator to back-calculate sequence parameters from conductor geometry.

## 3. What to check carefully
- Base voltage and base capacity must match the intended study base.
- Sequence resistance, reactance, and capacitance should use consistent units.
- Pay attention to the warning block if a parameter is outside typical reference ranges.

## 4. Common mistakes
- Confusing Ω/km with total Ω.
- Mixing microfarads and farads.
- Forgetting to convert the voltage base to the line-to-line RMS convention used by the page.

## 5. Engineering advice
Use this page as a front-end data-quality filter before the parameters are fed into fault, stability, or load-flow studies.

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

## Appendix F: Post-review notes
After each analysis, record at least the input version, operating mode, key judgment, action taken, and field feedback. Over time these records become a local experience base that improves consistency and speed.
