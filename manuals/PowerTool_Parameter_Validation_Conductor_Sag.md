# PowerTool Conductor Sag

## 1. Purpose
This page provides an engineering approximation for **single-span transmission-line conductor sag**. It uses a **catenary model with unequal support heights** and links sag to both **conductor temperature** and **current-induced temperature rise**.

It is suitable for early-stage studies, quick operating checks, teaching demonstrations, and sensitivity analysis. It is not a replacement for construction sag tables, long-term creep studies, wind/ice loading checks, or full IEEE 738 thermal-rating calculations.

## 2. Page layout
The left side contains three groups of inputs:

1. **Geometry and mechanical parameters**: span, left/right support heights, line mass, cross-section area, equivalent elastic modulus, thermal expansion coefficient, reference temperature, and reference horizontal tension.
2. **Current-to-temperature approximation**: ambient temperature, resistance at 20°C, resistance temperature coefficient, effective cooling coefficient, and solar heat gain.
3. **Interactive driving variables**: the conductor-temperature slider, the current slider, and the mode switch between **direct conductor temperature** and **current-derived temperature**.

The right side shows metric cards, a conductor sketch with the catenary, and a detailed result text block.

## 3. Calculation logic
### 3.1 Catenary geometry
The page assumes a single span with uniformly distributed self-weight:
- unequal support heights are allowed;
- it reports maximum sag from the support chord, midspan sag, minimum ground clearance, and support tensions;
- the plot overlays the **reference conductor** and the **current conductor** for direct comparison.

### 3.2 Temperature-to-tension coupling
The page starts from the user-defined `T_ref` and `H_ref` and solves the current horizontal tension using an engineering compatibility model based on:
- thermal expansion, and
- elastic extension evaluated from the average conductor tension.

This is well suited to questions such as:
- how much sag increases as conductor temperature rises,
- how clearance changes with unequal support heights,
- how the selected reference tension affects operating sag.

### 3.3 Current-to-temperature approximation
In **current-derived temperature** mode the page first estimates conductor temperature from the simplified steady-state balance

`I²R(T) + q_s = k_c (T_c - T_a)`

where:
- `R(T)` is the temperature-dependent conductor resistance,
- `q_s` is the effective solar heat gain,
- `k_c` is the effective cooling coefficient.

This model is intentionally lightweight so that the sliders remain responsive. It is not equivalent to IEEE 738.

## 4. Recommended workflow
1. Enter span, support heights, and a credible reference tension state.
2. If the conductor temperature is known, use **direct conductor temperature** mode and drag the temperature slider.
3. If the current is the main concern, use **current-derived temperature** mode and drag the current slider to observe the coupled change in temperature and sag.
4. Focus on four outputs:
   - maximum sag,
   - minimum ground clearance,
   - current horizontal tension,
   - sag increment relative to the reference state.

## 5. Input guidance
- **Line mass** should represent the conductor self-weight. If ice loading must be approximated, the extra load can be folded into this value, but the page does not explicitly separate wind and ice effects.
- **Equivalent elastic modulus** should preferably come from manufacturer data or an internal engineering standard.
- **Reference horizontal tension** should correspond to a known reference state such as 15°C no-wind/no-ice or 20°C initial tension.
- **Effective cooling coefficient** is a lumped engineering parameter. It should be calibrated from experience, historical temperature-rise observations, or existing thermal-rating knowledge rather than interpreted as a precise aerodynamic coefficient.

## 6. Interpreting the results
- **Maximum sag** is the largest downward offset from the straight chord between the two supports.
- **Midspan sag** is the sag at half span; it is not necessarily the maximum sag when the supports are at different heights.
- **Minimum clearance** is the most operationally relevant quantity because it directly measures the lowest conductor height above ground.
- **Horizontal tension** usually decreases as conductor temperature rises, which is why sag increases.

## 7. Limitations
The current page does not explicitly include:
- wind swing,
- ice loading and nonuniform added load,
- long-term creep,
- higher-order mechanical effects of bundled subconductors,
- tower deformation and insulator-string swing,
- detailed radiative and convective thermal modeling.

Therefore the page should be used as an **engineering approximation tool**, not as the sole basis for construction or formal operating documents.
