# PowerTool Manual - Parameter Validation & Per-Unit: Three-Winding Transformer

## 1. Purpose
This page converts three-winding transformer data into a study-base equivalent and checks the plausibility of the resulting leakage branches.

## 2. Notes before input
Confirm the rating and voltage data of all three windings, together with the pairwise short-circuit voltages and the intended study base.

## 3. Workflow
1. Enter the high-, medium-, and low-voltage winding data.
2. Provide the pairwise short-circuit voltages and the study base.
3. Run the conversion and inspect the equivalent T-model values and per-unit leakage branches.

## 4. Result interpretation
- Cross-check whether the three pairwise impedances lead to a physically meaningful equivalent.
- Large mismatch between winding ratings and impedance data often indicates an input problem rather than a modeling problem.

## 5. Recommendation
Use the page as a consistency check before building equivalent networks or protection-study models.

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
