# PowerTool Manual - Waveform Viewer

## 1. Function
The waveform page loads COMTRADE and related exported files, displays the selected channels, and supports sequence analysis, cursor measurements, and waveform export.

## 2. Supported formats
The page is designed for COMTRADE-style waveform data and the file formats already supported by the built-in parser. The viewer can also re-export waveforms into a normalized format when needed.

## 2.1 Re-export
Use the re-export function when a file opens but the metadata or channel interpretation is not suitable for the current study workflow.

## 3. Recommended workflow
1. Load the waveform file.
2. Verify the channel list and select the channels of interest.
3. Adjust the time window and vertical zoom.
4. Use cursors or sequence analysis to extract the quantities you need.
5. Export the processed view if a record is required.

## 4. Interpreting the result
- Channel overlays are useful for comparing phase relationships and transient trends.
- Sequence analysis highlights positive-, negative-, and zero-sequence content.
- Cursor measurements are useful for fault clearing time and oscillation-period checks.

## 5. Common issues
- Missing or mismatched channel mapping.
- Sampling-rate interpretation problems.
- Selecting too many channels at once and obscuring the trend.

## 6. Recommendation
Use this page as a lightweight waveform-inspection and teaching tool, then switch to specialized analysis software when a detailed protection or recorder study is required.

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
