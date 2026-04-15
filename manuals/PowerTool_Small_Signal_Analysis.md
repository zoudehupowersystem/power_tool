# PowerTool Manual - Small-Signal Analysis

## 1. Page function
This page performs an approximate SMIB small-signal study. It builds an operating point, numerically linearizes the nonlinear model, and reports eigenvalues, damping ratios, and participation factors.

## 2. Page composition
The page includes operating-point and network settings, model-configuration switching, and parameter pages for the sixth-order machine, AVR III, PSS II, and the Type-1 AVR/PSS validation page.

## 3. Recommended workflow
1. Build a baseline operating point in the operating-condition panel.
2. Choose the model configuration: generator only, generator + AVR, or generator + AVR + PSS.
3. Run the calculation and inspect the dominant mode, damping ratio, and participation factors.
4. If needed, switch to the Type-1 AVR/PSS validation page to check the control-block frequency-domain behavior.

## 4. Interpreting the result
- The rightmost eigenvalue indicates the stability margin in the linearized sense.
- The least-damped oscillatory mode is usually the first mode to watch.
- Participation factors help identify which states dominate the mode.

## 5. Common issues
- Failure to build a valid equilibrium point because the operating point and network parameters are inconsistent.
- Reading the result as a full multi-machine study; the page is still an SMIB approximation.
- Overinterpreting damping when the underlying operating point is poorly chosen.

## 6. Practical advice
Use the page to understand the sensitivity of modes to controller and network parameters before moving to larger eigenanalysis platforms.

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
