# PowerTool Manual - Overview

## 1. How to use the manual browser
Click **Manual** in the `PowerTool AI` sidebar. The manual browser opens with the document for the current page preselected. You can switch to any other manual from the list on the left.

## 2. Document structure
- Main-page manuals cover frequency dynamics, electromechanical oscillation, transient stability, small-signal analysis, loop closure, short-circuit calculation, and waveform viewing.
- Subpage manuals cover the voltage/reactive-power pages and the parameter-validation subpages.
- The files are stored in two parallel sets: English manuals use `PowerTool_*.md`, and Chinese manuals use `PowerTool_*_zh.md`.

## 3. Recommended reading order
1. Read the purpose and applicability limits of the current page.
2. Review the input definitions and the recommended workflow.
3. Run one complete example and check the result interpretation section.
4. Use the checklist and FAQ before exporting or acting on the conclusion.

## 4. Positioning of the manuals
These manuals guide engineering approximation studies inside PowerTool. They do not replace formal simulation reports, relay-setting documents, or grid-operation procedures.

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
