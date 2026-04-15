# PowerTool Manual - Short-Circuit Current Calculation

## 1. Function
This page estimates short-circuit currents, phase and sequence waveforms, phasor plots, and breaker-check quantities for typical line faults.

## 2. Input explanation
- Choose single-source or two-source mode.
- Define the system voltage, short-circuit capacity, line parameters, neutral-grounding mode, and transition resistance.
- For two-source mode, also define the right-side source strength and the fault location along the line.

## 3. Recommended steps
1. Select the fault type and network mode.
2. Enter the line and source parameters.
3. Run the page and review the summary card, waveform plots, and phasor table.
4. Compare the calculated breaking current with the breaker rating.

## 4. Reading the result
- Sequence components help explain the symmetry of the fault.
- The waveform panel shows the AC component plus the decaying DC offset.
- The breaker check is a quick engineering screen; it should be followed by a formal protection review when the margin is small.

## 5. Common mistakes
- Mixing total line impedance with per-kilometer input values.
- Using the wrong grounding mode.
- Forgetting to define the right-side system correctly in two-source studies.

## 6. Recommendation
Use the page for fast protection-oriented screening and for teaching the relationship between phase, sequence, and phasor quantities.

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
