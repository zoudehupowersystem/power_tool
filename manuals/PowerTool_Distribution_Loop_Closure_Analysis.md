# PowerTool Manual - Distribution Loop-Closure Analysis

## 1. Function
This page estimates steady-state loop current, section current distribution, and simplified impact transient current for distribution-network loop closure.

## 2. Input preparation
- Keep the voltage, angle, and impedance data on consistent physical bases.
- Make sure the connection-point numbering matches the intended topology.
- The closure point should correspond to an empty point with zero net current.

## 3. Step-by-step use
1. Run the steady-state analysis first and inspect the loop-current magnitude and direction.
2. Check the topology plot and the section-current table for overloaded sections.
3. Review the transient waveform tab to estimate the impact peak.
4. Adjust the phase-angle window or switching timing if the transient is too severe.

## 4. Reading the result
- Large steady-state loop current usually originates from voltage difference, angle difference, or impedance asymmetry.
- High transient peak current requires coordination checks for breaker capability and protection behavior.
- The ampacity check is a quick engineering screen rather than a replacement for full protection studies.

## 5. Common troubleshooting items
- Defining the wrong closure point.
- Mixing section impedance and total-loop impedance.
- Forgetting that the transient model is a simplified single-loop R-L superposition method.

## 6. Recommendation
At minimum, review normal load, heavy load, and maintenance-mode cases before approving a loop-closure scheme.

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
