# Approximate Constants and Approximate Formulas in Power Systems

[Chinese source](Approximate_Constants_and_Approximate_Formulas_in_Power_Systems_zh.md)

**Author: Dehu Zou**

## 1. Introduction

Power systems span multiple orders of magnitude. Voltage levels range from 10 kV to 1000 kV, transfer capacities from kW to GW, and network scale from a single substation to continent-scale interconnected grids. Yet, in contrast to these macroscopic differences, many important system parameters remain surprisingly conservative in order of magnitude. They are confined to relatively narrow intervals by underlying physical laws, such as electromagnetic-field equations and thermodynamic limits, and by engineering constraints, such as insulation strength and material limits. They do not expand in proportion to system scale. These “approximate constants” are valuable clues for developing engineering intuition in power-system analysis. They can also serve as practical checks on data plausibility: once a parameter deviates markedly from these ranges, it is often worth re-examining the input.

Power-system operation has also developed a family of approximate formulas that goes beyond ordinary textbook treatment. These formulas are built on simplified assumptions: a multi-machine system is reduced to a single-machine equivalent, complex loads are linearized into frequency damping, dispersed primary-frequency response is represented by a first-order link, long transmission lines are summarized through surge impedance and natural power, and transient-stability assessment is reduced to linearized impact quantities. The cost of simplification is, of course, approximation error. Its value is equally clear: it exposes the physical essence behind simulation results and helps analysts build a conceptual understanding before detailed simulation is carried out. In other words, approximate formulas are not intended to replace detailed simulation. Their role is to explain why a result falls in a given range and why it changes in a certain direction.

This paper places these two layers into a single framework. Section 2 establishes a unified notation to avoid ambiguity in later derivations. Section 3 reviews approximate constants in power-system equipment parameters and explains why they remain stable over wide engineering ranges. Sections 4 through 8 derive and interpret the approximate formulas with the strongest engineering explanatory power for frequency dynamics, electromechanical oscillation, voltage stability, line reactive-power behavior, and transient stability. Section 9 presents an integrated set of worked examples to show how these formulas are actually used in engineering estimation. Section 10 discusses the boundaries of applicability and the sources of error.

---

## 2. Symbol Conventions

To avoid confusion in units, the following conventions are adopted.

**Per-unit and dimensional quantities.** In the frequency-dynamics sections, all variables are assumed by default to be expressed in per unit on a common base. Thus, power deficit, frequency deviation, load-frequency coefficient, and primary-frequency-response coefficient are all normalized on the same base. If dimensional units are used instead, such as MW and Hz, then the coefficient units must be modified consistently. For example, if $\Delta f$ is expressed in Hz and $\Delta P$ in MW, then $k_D$ and $k_G$ must be expressed in MW/Hz. One must not directly mix per-unit formulas with dimensional formulas.

**Main symbols used in this paper:**

| Symbol | Meaning |
| :--- | :--- |
| $H$ | Inertia constant of a single generator (s), defined as the ratio of rotor kinetic energy to rated capacity, $H = E_k / S_N$ |
| $T_s$ | Equivalent system inertia time constant (s), used in frequency dynamics, corresponding to the aggregated network inertia; $T_s = 2H$ |
| $T_j$ | Inertia time constant of a single generator (s), used in single-machine oscillation and transient-stability analysis; $T_j = 2H$ |
| $T_G$ | Aggregate primary-frequency-response time constant (s) |
| $k_D$ | Load-frequency regulation coefficient (per unit) |
| $k_G$ | Static power-frequency droop coefficient of generating units (per unit) |
| $k_s$ | $k_D + k_G$, the aggregate system frequency-regulation coefficient |
| $K_s$ | Synchronizing torque coefficient (per unit), appearing throughout electromechanical-oscillation and transient-stability analysis |
| $E'_q$ | Generator transient EMF (per unit) |
| $U$, $U_g$ | Bus voltage and sending-end voltage (per unit) |
| $X_\Sigma$ | Equivalent reactance (per unit) |
| $Z_c$ | Surge impedance of a transmission line (Ω) |
| $P_N$ | Natural power of a transmission line (MW) |
| $\omega_0$ | Rated angular frequency of the system (rad/s); for a 50 Hz system, $\omega_0 = 2\pi \times 50 \approx 314$ rad/s |

Note that $T_s$ and $T_j$ do not mean the same thing. $T_j$ refers to a single unit, whereas $T_s$ is an aggregated system quantity. They correspond to the same machine only in single-machine-infinite-bus analysis. In multi-machine equivalent models, $T_s$ should be understood as the weighted aggregate of the system inertia.

---

## 3. Approximate Constants of Power-System Equipment

After fixing the notation, it is helpful to build intuition for equipment parameters themselves before deriving dynamic formulas. Several approximate constants appear in power-system equipment parameters. They remain relatively stable over broad ranges of voltage level and capacity, and each has a clear physical mechanism behind it. These constants are important prerequisites for the approximate formulas that follow. In particular, the discussion of the generator inertia constant $H$ in Section 3.6 provides the order-of-magnitude basis for the formulas in Sections 4, 5, and 8.

### 3.1 The “Constancy” of the Current-Carrying Capacity of a Single Conductor

Regardless of voltage level, the rated current-carrying capacity of a single subconductor in an overhead line typically remains in the range of about 400 A to 1000 A.

The root cause is the thermal-balance mechanism of the conductor. Steady-state ampacity is determined by the balance between Joule heating and surface heat dissipation. The maximum allowable current $I_{\max}$ scales with conductor radius $r$ approximately as

$$I_{\max} \propto r^{1.5}$$

Because of skin effect and the mechanical difficulty of manufacturing and stringing very large conductors, the physical diameter of a single conductor is tightly constrained, which in turn constrains the upper current limit of a single conductor.

Engineering practice confirms this rule. A 10 kV overhead distribution line uses a single conductor with an ampacity of around 400 A. A 500 kV backbone line, in contrast, achieves large power transfer by using bundled conductors, for example four subconductors each carrying roughly 577 A. The average current per subconductor still lies in the same range. Higher voltage levels increase total current capacity by increasing the bundle number rather than by substantially increasing the physical limit of a single conductor.

### 3.2 Wave Velocity and Surge Impedance of Overhead Transmission Lines

For an overhead transmission line, the theoretical wave velocity is

$$v = \frac{1}{\sqrt{LC}} = \frac{1}{\sqrt{\mu_0 \varepsilon_0}} \approx 3 \times 10^5 \text{ km/s}$$

which is exactly the speed of light in vacuum. Here $L$ is the inductance per unit length (H/m) and $C$ is the capacitance per unit length (F/m). In practice, wave velocity is slightly lower because of skin effect and earth-return losses, but it still remains very close to the speed of light.

Equally important is the surge impedance, also called the characteristic impedance,

$$Z_c = \sqrt{\frac{L}{C}}$$

The surge impedance does not vary greatly across voltage levels, although it is not a strict constant. This has direct engineering significance: **the natural power of a transmission line depends mainly on the operating voltage and only weakly on the specific line parameters.** This gives a very convenient estimation path for reactive-power balance in EHV and UHV lines, a topic developed in Section 7.

### 3.3 Positive-Sequence Reactance per Unit Length of Overhead Lines

At 50 Hz, the positive-sequence reactance of a three-phase overhead line is commonly in the range of 0.2 to 0.4 Ω/km, almost independent of voltage level. The theoretical explanation comes from the geometric-mean-distance formula:

$$x_1 \approx 0.1445 \log_{10}\!\left(\frac{D_{eq}}{D_s}\right) + 0.0157 \quad (\Omega/\text{km})$$

As voltage level rises, phase-to-phase insulation requirements increase the equivalent geometric mean distance $D_{eq}$. At the same time, bundle conductors must be adopted to suppress corona, which increases the self geometric mean distance $D_s$. Since numerator and denominator grow together, the logarithmic term changes only modestly. As a result, $x_1$ remains comparatively stable over a wide voltage range.

### 3.4 Summary of Typical Line Parameters

The following table gives typical line parameters at different voltage levels, based on the *Power System Design Manual* issued by the Electric Power Planning & Engineering Institute. Wave velocity and surge impedance $Z_c$ are calculated from $X_1$ and $C_1$.

| Voltage level | Line type | $R_1$ (Ω/km) | $X_1$ (Ω/km) | $C_1$ (μF/km) | Wave velocity (km/s) | $Z_c$ (Ω) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1000 kV | 8×LGJ-500 | 0.0076 | 0.264 | 0.0139 | 292600 | 246 |
| 500 kV | 4×LGJQ-300 | 0.027 | 0.280 | 0.0128 | 296000 | 264 |
| 220 kV | 2×LGJJ-240 | 0.065 | 0.303 | 0.0119 | 295400 | 285 |
| 110 kV | LGJ-150 | 0.63 | 0.442 | 0.00808 | 296700 | 417 |

The table shows several features directly: $X_1$ is almost the same for the first three voltage levels, propagation velocity is close to the speed of light at all levels, and surge impedance decreases gradually as voltage level increases, which is one reason why higher-voltage lines have greater natural power.

### 3.5 Consistency of Transformer Percent Short-Circuit Impedance

The percent short-circuit impedance of a transformer, $U_k\%$, is remarkably consistent across a huge capacity range. From a 10 kVA pole-mounted transformer to a 1000 MVA UHV main transformer, $U_k\%$ usually lies in a narrow band of about 4% to 15%. UHV main transformers are somewhat higher, typically around 18% to 24%.

This range is set by two opposing constraints. **The lower bound is mechanical strength.** During a short circuit, the electromagnetic force on the winding scales as $F \propto (1/U_k\%)^2$. If $U_k\%$ is too small, short-circuit force increases quadratically and may damage the transformer instantly. **The upper bound is grid operation.** If $U_k\%$ is too large, the voltage regulation under normal loading becomes too poor, and the secondary voltage fluctuates excessively with load, making supply-quality requirements difficult to satisfy. The intersection of these two constraints confines $U_k\%$ to a relatively stable interval rather than allowing order-of-magnitude growth with transformer size.

### 3.6 Two Approximate Constants of Rotating Electrical Machines

**The “physical ceiling” of generator terminal voltage**

Generator capacity may rise from 10 MW to 1000 MW, yet the rated terminal voltage increases only slowly, from around 10.5 kV to roughly 27 kV, indicating a clear physical upper bound. The reason is that slot space in the stator is extremely precious. A large increase in terminal voltage requires a much thicker insulation layer. Insulation has poor thermal conductivity and occupies space that would otherwise be available for copper conductor cross-section, so the effective output capability of the machine may actually decrease.

**The stability of the inertia constant $H$**

Across a wide range of synchronous-generator capacities, the inertia constant $H$ usually remains in the range of 2 to 6 s. The fundamental reason is that both **power density** and **rotational energy density** are constrained by the same set of physical limits.

- The upper limit of power density is set by electromagnetic loading in the stator slots. Conductor current density is limited by the heat-removal capability of copper, while air-gap flux density is limited by the saturation of silicon steel. As a result, the electric power output per unit volume is roughly bounded.
- The upper limit of rotational energy density is determined by rotor material strength. Rotor surface speed is constrained by the yield strength of steel, which limits the maximum kinetic energy that can be stored per unit rotor mass.

Since both are locked by material limits, and because increasing machine size increases both kinetic energy and power at the same time, the ratio $H$ naturally remains stable over a wide capacity range.

This conclusion will be used repeatedly later. In the frequency-dynamics analysis of Section 4, the equivalent system inertia time constant $T_s$ is the weighted aggregate of generator $H$ values, and large interconnected systems are usually in the range of 8 to 15 s. In Sections 5 and 8, where electromechanical oscillation and transient stability are considered, the typical range of single-machine $T_j$ values, about 4 to 10 s, directly determines the order of magnitude of oscillation frequency and critical clearing time.

---

## 4. Approximate Frequency Dynamics: From a First-Order Model to a Second-Order Model with Primary Frequency Control

The previous section established intuition for equipment parameters, especially the inertia constant $H$, which sets the scale of the aggregated system inertia $T_s$. Starting from the swing equation and taking $T_s$ as the central parameter, this section derives the four quantities of greatest engineering value during the post-disturbance frequency response: the initial rate of change of frequency, the steady-state frequency deviation, the time at which the nadir occurs, and the frequency nadir itself.

### 4.1 First-Order Model: Inertia and Load-Frequency Characteristic Only

The most basic starting point for frequency dynamics is the swing equation. If the system is represented as a single equivalent machine feeding a lumped load, and the mechanical power is assumed temporarily constant immediately after a disturbance, then in power form one may write

$$M\frac{d\omega}{dt} = P_m - P_L$$

If the load has a frequency characteristic, it may be expressed as $P_L = P_0(f/f_0)^{K_L}$. Linearizing near rated frequency gives

$$\Delta P_L \approx D\,\Delta f, \qquad D = \frac{K_L P_0}{f_0}$$

Converting the physical inertia $M$ into the equivalent system inertia time constant $T_s$, and assuming an initial active-power deficit $\Delta P_{OL0}$ caused by the disturbance, one obtains the first-order frequency equation

$$T_s\frac{d\Delta f}{dt} + k_D\Delta f = -\Delta P_{OL0}$$

Let $T_f = T_s/k_D$. The first-order solution for frequency deviation is then

$$\Delta f(t) = -\frac{\Delta P_{OL0}}{k_D}\left(1 - e^{-t/T_f}\right)$$

This result reveals three important facts. First, if the system has only load-frequency sensitivity and no primary-frequency response, the frequency decline is monotonic; there is no “dip then recovery” behavior. Second, the larger the time constant $T_f = T_s/k_D$, the slower the decline. Third, the steady-state frequency deviation is

$$\Delta f_\infty = -\frac{\Delta P_{OL0}}{k_D}$$

Thus, with load-frequency sensitivity alone, the frequency settles at a new equilibrium offset from rated value. This is exactly why primary frequency control and AGC are needed, and it leads naturally to the second-order model in the next subsection.

### 4.2 Second-Order Model: Including Primary Frequency Control

The model of greatest practical value for operators is the second-order approximation that includes primary frequency response:

$$T_s\frac{d\Delta f}{dt} = -\Delta P_{OL}$$

$$T_G\frac{d\Delta P_G}{dt} + \Delta P_G = -k_G\Delta f$$

$$\Delta P_D = k_D\Delta f, \qquad \Delta P_{OL} = \Delta P_D - \Delta P_G + \Delta P_{OL0}$$

The structure is transparent. Inertia determines how fast the system initially starts to fall. Load-frequency sensitivity and primary frequency control then determine whether the decline can be arrested and to what level it will eventually settle.

Eliminating the intermediate variables yields the second-order constant-coefficient differential equation for $\Delta f$:

$$T_sT_G\frac{d^2\Delta f}{dt^2} + \left(T_s + k_DT_G\right)\frac{d\Delta f}{dt} + \left(k_D + k_G\right)\Delta f + \Delta P_{OL0} = 0$$

Let $k_s = k_D + k_G$, $T_f = T_s/k_D$, and define

$$\alpha = \frac{1}{2}\left(\frac{1}{T_G} + \frac{1}{T_f}\right), \qquad \Omega = \sqrt{\frac{k_s}{T_sT_G} - \alpha^2}$$

When $k_s/(T_sT_G) > \alpha^2$, the system is underdamped, and the frequency response can be written as

$$\Delta f(t) = -\frac{\Delta P_{OL0}}{k_s}\left[1 - 2A_m e^{-\alpha t}\cos(\Omega t + \varphi)\right]$$

where

$$A_m = \frac{1}{2\Omega T_s}\sqrt{k_sk_G}, \qquad \varphi = \arctan\!\left(\frac{1}{\Omega}\left(\frac{k_s}{T_s} - \alpha\right)\right)$$

This expression contains the three most important features of post-disturbance frequency dynamics: an overall negative offset, whose scale is set by $\Delta P_{OL0}/k_s$; an exponential decay rate, governed mainly by $\alpha$; and the pace of the swing-and-recovery behavior, governed mainly by $\Omega$.

### 4.3 Four Quantities of Greatest Engineering Value

#### (1) Initial rate of change of frequency

At the instant when the disturbance occurs, neither primary frequency response nor load-frequency response has had time to fully develop. Therefore,

$$\boxed{\left.\frac{d\Delta f}{dt}\right|_{0^+} = -\frac{\Delta P_{OL0}}{T_s}}$$

**The initial ROCOF depends only on the power deficit and the system inertia.** The larger the inertia, the more sluggish the system at the instant of the event. The larger the deficit, the steeper the initial decline. Combined with the conclusion of Section 3.6, this means that in grids with high renewable penetration, where conventional synchronous machines are replaced by inverter-based resources, reduced equivalent inertia can significantly increase frequency vulnerability.

#### (2) Steady-state frequency deviation

Letting $t \to \infty$, the exponential term vanishes, so that

$$\boxed{\Delta f_\infty = -\frac{\Delta P_{OL0}}{k_s} = -\frac{\Delta P_{OL0}}{k_D + k_G}}$$

The load-frequency characteristic and the static primary-frequency droop characteristic contribute in parallel at steady state. Full restoration to nominal frequency still requires secondary frequency control, that is, AGC.

#### (3) Time of the frequency nadir

In the underdamped case, setting the derivative of the frequency response to zero gives the time $t_m$ at which the nadir occurs. The safest form is

$$t_m = \frac{1}{\Omega}\operatorname{atan2}\!\left(2T_sT_G\Omega,\; k_DT_G - T_s\right)$$

The use of $\operatorname{atan2}$ instead of the ordinary inverse tangent is deliberate. In practical parameter ranges, the denominator $k_DT_G - T_s$ may be negative. If one uses the principal value of $\arctan$ directly, the quadrant may be chosen incorrectly, leading to a negative nadir time or a value from the wrong branch.

#### (4) Frequency nadir

Substituting $t_m$ into the frequency-response expression and using the zero-derivative condition at the nadir yields

$$\boxed{\Delta f_{\min} = -\frac{\Delta P_{OL0}}{k_s}\left(1 + \sqrt{\frac{k_GT_G}{T_s}}\;e^{-\alpha t_m}\right)}$$

This expression holds in the underdamped case when the response has a well-defined nadir. If the parameters make the second-order response overdamped, the curve decays monotonically toward steady state and no “drop then recovery” nadir exists, so the above formula should not be applied mechanically. The dimensional minimum frequency is $f_{\min} = f_0(1 + \Delta f_{\min})$.

### 4.4 Physical Interpretation of Parameter Sensitivity

A systematic sensitivity reading of the formulas above is useful for quickly locating the dominant cause of a problem in engineering practice.

- **Larger $T_s$** directly reduces the initial ROCOF, but has almost no direct effect on the steady-state frequency deviation or the nadir level. What determines how steep the initial frequency drop is, is inertia rather than primary-control parameters.
- **Larger $k_G$** significantly reduces the steady-state frequency deviation and usually raises the nadir. However, $k_G$ does not determine how fast the primary response is established. That speed is reflected more in $T_G$.
- **Larger $T_G$** means slower establishment of primary response. The nadir is typically lower and occurs later. Cases where “the steady-state value is acceptable but the nadir is dangerously deep” often reflect insufficient response speed rather than insufficient static droop.
- **The role of $k_D$ is often underestimated.** Load-frequency sensitivity is not a controller, yet it provides persistent natural damping after a disturbance. It is the first buffering layer that requires no explicit control action.

---

## 5. Approximate Formula for Electromechanical Oscillation Frequency

The frequency dynamics discussed in the previous section concern the active-power-frequency coupling of the entire grid over a time scale of seconds to minutes. The key parameter there is the aggregated system inertia $T_s$. Once attention shifts to the relative swing of a single machine, or a machine group, against the rest of the system, one enters the domain of electromechanical oscillation. The time scale becomes shorter, typically 0.5 to 5 s, and the key parameters become the single-machine inertia time constant $T_j$ and the synchronizing torque coefficient $K_s$.

### 5.1 Basic Derivation

The classical approximation for electromechanical oscillation comes from the linearized swing equation. Let $\delta$ be the power angle between the generator and the system, and let the unit inertia time constant be $T_j$. For a small disturbance around the operating point $\delta_0$, neglecting damping torque and mechanical-power perturbation, the swing equation is

$$\frac{T_j}{\omega_0}\frac{d^2\Delta\delta}{dt^2} = -\Delta P_e$$

Using generator transient EMF $E'_q$, system-side voltage $U$, and equivalent reactance $X_\Sigma$, the electrical power follows the power-angle relation

$$P_e = \frac{E'_qU}{X_\Sigma}\sin\delta$$

Linearizing at the operating point $\delta_0$ gives

$$\Delta P_e = K_s\,\Delta\delta, \qquad K_s = \frac{E'_qU}{X_\Sigma}\cos\delta_0$$

$K_s$ is called the **synchronizing torque coefficient**. It represents the restoring capability of electrical power when the power angle departs from equilibrium. Substituting into the swing equation yields the standard undamped oscillation equation, whose natural oscillation frequency is

$$\boxed{f_n = \frac{1}{2\pi}\sqrt{\frac{\omega_0 K_s}{T_j}}}$$

The synchronizing torque coefficient can also be rewritten as

$$K_s = P_0\cot\delta_0$$

This form is highly instructive. For the same power output, a larger power angle means a smaller $\cot\delta_0$, weaker synchronizing stiffness, and thus a lower oscillation frequency. This is the microscopic mechanism behind the greater tendency of heavily loaded, long-distance transmission corridors to exhibit low-frequency oscillation. Combined with Section 3.6, where typical $T_j$ values are 4 to 10 s, and with representative $K_s \approx 1$ to $2$ pu, the formula indeed gives oscillation frequencies in the 1 to 2 Hz range of local modes.

### 5.2 A Frequently Misunderstood Point

In informal discussion one often hears that “low-frequency oscillation is caused by the governor or the exciter.” Strictly speaking, this is not accurate. The oscillation frequency itself is determined primarily by synchronizing stiffness and inertia, namely by $K_s$ and $T_j$. Control devices such as governors, exciters, and PSSs mainly affect **damping** and modal coupling. They influence whether an oscillation is amplified or suppressed, and how fast it decays, rather than fundamentally creating an oscillation frequency that did not already exist.

A more rigorous statement is that a disturbance excites electromechanical modes already present in the system. Controller parameters mainly change the damping ratio and participation factors of these modes. In some cases they may also shift the frequency indirectly by changing the operating point or the effective synchronizing stiffness, but their primary role is not to create the oscillation frequency from nothing.

It is worth noting that the $K_s$ in this section and the $K_s^{\text{post}}$ used in the transient-stability analysis of Section 8 have exactly the same algebraic form. The difference is that the latter is evaluated using the post-fault network parameters. This is not accidental. The linearized swing equation has the same physical structure in both small-disturbance analysis and impact-method approximation.

---

## 6. Approximate Formulas Related to Voltage

The approximate analyses of frequency and power angle mainly concern active power and rotating-machine dynamics. Yet power systems also contain another equally important dimension: the balance between bus voltage and reactive power. This section presents the three most commonly used voltage approximations, progressing from the static voltage-stability limit to quick bus-voltage estimation and then to the estimation of capacitor-switching effects.

### 6.1 Maximum Transmittable Active Power at the Receiving End

Consider a typical two-bus system. A source of voltage $U_g$ feeds a receiving-end load through a total reactance $X_\Sigma$. Resistance is neglected, and the load power-factor angle is $\varphi$. The maximum transmittable active power corresponding to the static voltage-stability limit is

$$\boxed{P_{L,\max} = \frac{U_g^2}{2X_\Sigma}\frac{\cos\varphi}{1 + \sin\varphi}}$$

When the power factor is unity, this reduces to $P_{L,\max} = U_g^2/(2X_\Sigma)$. This formula reveals two important points. A larger line reactance lowers the voltage-stability limit, and a more lagging load power factor also lowers the limit. This is not the same as the power-angle limit in the transient-stability discussion of Section 8, but both reflect a common fact: once the effective system stiffness decreases, the transferable load level also decreases.

### 6.2 Minimum Receiving-End Voltage

Under the same assumptions, when the load reaches the static voltage-stability limit, the receiving-end voltage reaches its minimum value:

$$\boxed{V_{\min} = \frac{1}{\sqrt{2 + 2\sin\varphi}}}$$

Here the voltage is normalized on the sending-end base. Several representative values are worth remembering:

- When $\cos\varphi = 1$, $V_{\min} = 1/\sqrt{2} \approx 0.707$
- When $\cos\varphi = 0.95$, $V_{\min} \approx 0.617$
- When $\cos\varphi = 0.707$, that is, $P = Q$, $V_{\min} \approx 0.541$

These values give operators a direct intuition: **the poorer the load power factor, the more likely it is that once the receiving-end voltage falls below a certain threshold, the system is already very close to static voltage collapse.**

### 6.3 Quick Estimation of Bus Voltage and the Effect of Capacitor Switching from $P$ and $Q$

Represent the external system seen from the bus of interest by a Thevenin source, with equivalent EMF $E$ and equivalent impedance $jX_i$. If the active and reactive powers received by the bus from the system are $P$ and $Q$, then after eliminating the phase angle one obtains

$$P^2 + \left(Q + \frac{U^2}{X_i}\right)^2 = \frac{E^2U^2}{X_i^2}$$

Let $S = E^2/X_i$, which may be interpreted as the short-circuit capacity seen from the bus, and let $y = (U/E)^2$. The equation becomes

$$y^2 + \left(\frac{2Q}{S} - 1\right)y + \frac{P^2 + Q^2}{S^2} = 0$$

Taking the physically meaningful root near the operating point gives

$$\left(\frac{U}{E}\right)^2 = \frac{1}{2}\left[1 - \frac{2Q}{S} + \sqrt{\left(1 - \frac{2Q}{S}\right)^2 - \frac{4(P^2 + Q^2)}{S^2}}\right]$$

When the system is strong and $P,Q \ll S$, a further expansion yields

$$\frac{U}{E} \approx 1 - \left(\frac{Q}{S} + \frac{P^2}{2S^2}\right)$$

The engineering meaning is immediate. Bus voltage is much more sensitive to reactive power than to active power, whose influence is usually only second order. Thus, when bus voltage fluctuates in operation, the first suspicion should typically be reactive-power imbalance rather than active-power flow itself.

Differentiating the expression above, and considering the practically important case of **shunt-capacitor switching** where usually $\Delta P \approx 0$, one immediately obtains the most useful quick-estimation formula:

$$\boxed{\Delta U\,(\text{pu}) \approx \frac{\Delta Q_c}{S}}$$

Here $\Delta Q_c$ is the capacitive reactive power injected at the bus, taken as positive for switching in, and $S$ is the short-circuit capacity of the bus. This formula reveals an extremely important operational fact: **the same capacitor bank has only a limited voltage effect on a strong-system bus, but a much stronger effect on a weak-system bus.** This explains why the same shunt capacitor installed at buses with different short-circuit capacities can produce very different voltage steps.

---

## 7. Approximate Formulas for Natural Power and Reactive-Power Loss of Transmission Lines

Section 3.2 showed that the surge impedance $Z_c$ does not vary greatly with voltage level. A direct consequence is that the natural power of a line can be estimated by a very concise formula, from which a highly practical criterion for the reactive behavior of long lines follows. This complements the voltage-reactive-power analysis of Section 6. Section 6 focuses on bus-node reactive balance, whereas this section focuses on the reactive characteristics of the transmission line itself.

### 7.1 Natural Power

For a lossless long transmission line, the natural power at rated voltage is

$$\boxed{P_N = \frac{U^2}{Z_c}}$$

The physical meaning is profound. When the active power transmitted by the line is equal to the natural power, the reactive power consumed by line inductance is approximately balanced by the reactive power generated by line capacitance. The line therefore behaves as if it were approximately self-balanced in reactive power.

### 7.2 Estimation of Reactive-Power Loss

Suppose the charging power per unit length at rated voltage is $Q_N$, the line length is $l$, and the actual active-power transfer is $P$. Then the approximate reactive-power loss, or surplus, of the line is

$$\boxed{\Delta Q_L = \left[\left(\frac{P}{P_N}\right)^2 - 1\right]Q_N l}$$

This formula leads to two very important judgments:

- If $P < P_N$, then $\Delta Q_L < 0$, meaning that the line **generates net reactive power** and behaves capacitively.
- If $P > P_N$, then $\Delta Q_L > 0$, meaning that the line **absorbs net reactive power** and behaves inductively.

Natural power is therefore not merely a “power value”; it is a **boundary point** separating the net-capacitive region from the net-inductive region of long-line reactive behavior, and it directly determines the direction of voltage-control strategy. This criterion can be used together with the capacitor-switching estimate of Section 6.3: the line reactive-power balance indicates the direction in which compensation is needed, while the capacitor-switching formula indicates the associated voltage change.

---

## 8. Approximate Estimation of the Transient-Stability Limit

The preceding sections established approximate analysis frameworks from three perspectives: frequency in Section 4, small-disturbance power-angle behavior in Section 5, and voltage-reactive-power behavior in Sections 6 and 7. This section returns to angle stability, but the concern is no longer linearized small-disturbance oscillation. Instead, it is a large disturbance: the competition between the energy impact accumulated during the fault and the ability of the system to restore synchronism after fault clearing. This is the core of transient-stability analysis. Accurate evaluation requires full time-domain simulation, but engineering quick estimation is still highly valuable.

### 8.1 The Engineering Idea of the Impact Method

Strict transient-stability analysis uses the equal-area criterion or complete time-domain simulation. For a single-machine-infinite-bus system, the equal-area criterion is written as

$$\int_{\delta_0}^{\delta_c}(P_m - P_{e,f})\,d\delta = \int_{\delta_c}^{\delta_{\max}}(P_{e,\text{post}} - P_m)\,d\delta$$

In engineering quick estimation, the **impact method** follows a simpler intuition. The fault gives the rotor a “kick.” The strength of that kick, namely the accelerating power $\Delta P_a$, multiplied by its duration $\Delta t$, determines how much initial speed is accumulated by the rotor. The system elasticity, represented by the post-fault synchronizing torque coefficient $K_s^{\text{post}}$, and the inertia, represented by $T_j$, then determine how large the resulting power-swing amplitude will be. This is physically consistent with the small-disturbance picture of Section 5; it is a transition from linearized free oscillation to forced response under a large disturbance.

### 8.2 Derivation

**Step 1: rotor speed deviation accumulated at fault clearing**

During the fault, the accelerating power is approximated as a constant $\Delta P_a$. Integrating over the fault duration $\Delta t$ gives the rotor speed deviation at the clearing instant:

$$\Delta\omega_{cl} = \frac{\omega_0\,\Delta P_a}{T_j}\,\Delta t$$

**Step 2: free oscillation after fault clearing**

After clearing, the rotor oscillates freely around the new equilibrium point of the post-fault network,

$$\delta_s = \arcsin(P_m/P_{\max}^{\text{post}})$$

with oscillation angular frequency

$$\omega_n = \sqrt{\frac{\omega_0 K_s^{\text{post}}}{T_j}}, \qquad K_s^{\text{post}} = P_{\max}^{\text{post}}\cos\delta_s$$

**Step 3: convert angle amplitude to power amplitude**

The one-sided amplitude of power oscillation, that is, the maximum overshoot, is

$$A = K_s^{\text{post}} \cdot \frac{\Delta\omega_{cl}}{\omega_n} = \omega_n \cdot \Delta P_a \cdot \Delta t$$

Using the frequency form $\omega_n = 2\pi f_d$, one obtains

$$\boxed{A = 2\pi f_d \cdot \Delta P_a \cdot \Delta t}$$

**Important note:** here $f_d$ must be calculated from the **post-fault** network parameters, namely $K_s^{\text{post}}$ and $T_j$. The pre-fault operating point must not be reused.

### 8.3 Stability Condition and Transient-Stability Limit

During the first swing, the peak power must not exceed the maximum transmittable power of the post-fault network $P_{\max}^{\text{post}}$, otherwise the system loses synchronism. Therefore, the estimated transient-stability limit is

$$\boxed{P_{st} \approx P_{\max}^{\text{post}} - D_p}$$

where $D_p = 2\pi f_d \cdot \Delta P_a \cdot \Delta t$ is defined as the one-sided amplitude. In some references, however, $D_p$ is defined as the total peak-to-peak swing. In that case the formula becomes $P_{st} \approx P_{\max}^{\text{post}} - D_p/2$. One must confirm the definition of $D_p$ before applying the formula. This is one of the most common sources of hand-calculation error in the impact method.

### 8.4 Critical Clearing Angle and Critical Clearing Time

The impact method answers the question: given a clearing time, how large will the swing amplitude be? Protection engineers are often more concerned with the complementary question: **within what time must the fault be cleared so that the system will not lose synchronism?** For a three-phase metallic short circuit during which $P_{e,f} \approx 0$, the equal-area criterion gives the critical clearing angle

$$\delta_{cr} = \arccos\!\left[\frac{P_m}{P_{\max}}(\pi - 2\delta_0) - \cos\delta_0\right]$$

From uniform-acceleration integration, the critical clearing time is

$$\boxed{t_{cr} \approx \sqrt{\frac{2T_j(\delta_{cr} - \delta_0)}{\omega_0\,P_m}}}$$

where $\delta_{cr} - \delta_0$ is expressed in radians, and $P_{\max}$ should be the maximum transmittable power of the **post-fault** network.

The impact method and the critical-clearing-time formula form a two-layer structure. The impact method gives a quick estimate of the risk level, while the $t_{cr}$ formula checks whether relay action time is adequately fast. They characterize the same physical constraint from different directions and therefore complement one another.

---

## 9. Integrated Worked Examples

The following examples illustrate how the approximate formulas can be used in a “dispatch quick-estimation” setting. All sub-problems share the same general system background. The purpose is not high-fidelity simulation, but to demonstrate the calculation process and its physical interpretation.

### 9.1 Estimating the Frequency Nadir After a Disturbance

Consider a receiving-end system operating at 50 Hz on a 10 GW system base. A major disturbance causes an active-power deficit of 800 MW, namely $\Delta P_{OL0} = 0.08$ pu. Let the equivalent parameters be

$$T_s = 8\text{ s}, \quad T_G = 5\text{ s}, \quad k_D = 1.2, \quad k_G = 4.0$$

Then $k_s = k_D + k_G = 5.2$ and $T_f = T_s/k_D = 6.667$ s. Further,

$$\alpha = \frac{1}{2}\left(\frac{1}{5} + \frac{1}{6.667}\right) = 0.175\text{ s}^{-1}, \qquad \Omega = \sqrt{\frac{5.2}{8 \times 5} - 0.175^2} \approx 0.315\text{ s}^{-1}$$

**Initial ROCOF**

$$\left.\frac{df}{dt}\right|_{0^+} = -\frac{0.08}{8} \times 50 = -0.50\text{ Hz/s}$$

**Steady-state frequency deviation**

$$\Delta f_\infty = -\frac{0.08}{5.2} \approx -0.769\text{ Hz}, \quad f_{ss} \approx 49.231\text{ Hz}$$

**Time of the nadir**

$$t_m = \frac{1}{0.315}\operatorname{atan2}(2 \times 8 \times 5 \times 0.315,\;1.2 \times 5 - 8) \approx 5.23\text{ s}$$

**Frequency nadir**

$$\Delta f_{\min} = -\frac{0.08}{5.2}\left(1 + \sqrt{\frac{4.0 \times 5}{8}}\,e^{-0.175 \times 5.23}\right) \approx -0.02512\text{ pu}$$

Hence,

$$f_{\min} = 50 \times (1 - 0.02512) \approx 48.744\text{ Hz}$$

For comparison, if primary frequency response is completely ignored and only the pure first-order model is used, the frequency at the same instant is about 48.185 Hz, and the deepest point is roughly 0.56 Hz lower. This shows that **the contribution of primary frequency control is not limited to steady-state improvement. It significantly reshapes the most dangerous few seconds immediately after the disturbance.**

### 9.2 Estimating Electromechanical Oscillation Frequency of a Generator

Consider a sending-end generator connected to the system through an equivalent reactance $X_\Sigma = 0.55$. Let $E'_q = 1.12$ pu, $U = 1.0$ pu, initial active-power output $P_0 = 0.8$ pu, and $T_j = 9$ s.

First compute the initial power angle:

$$\delta_0 = \arcsin(0.8 \times 0.55 / 1.12) \approx 23.1^\circ$$

The synchronizing torque coefficient is

$$K_s = \frac{1.12}{0.55}\cos 23.1^\circ \approx 1.873$$

Hence the small-disturbance oscillation frequency is

$$f_n = \frac{1}{2\pi}\sqrt{\frac{314 \times 1.873}{9}} \approx 1.29\text{ Hz}$$

This value lies in the typical range of local electromechanical oscillation modes. If a line outage increases $X_\Sigma$, or if greater machine output increases $\delta_0$, then $K_s$ decreases and the oscillation frequency also decreases. This is the microscopic mechanism behind the increase in oscillation risk when transfer across a transmission corridor rises.

### 9.3 Estimating the Static Voltage-Stability Limit

Consider a receiving-end load supplied from a source of $U_g = 1.0$ pu through a total reactance $X_\Sigma = 0.32$. Let the load power factor be $\cos\varphi = 0.95$, so that $\sin\varphi \approx 0.312$.

The maximum transmittable active power is

$$P_{L,\max} = \frac{1.0^2}{2 \times 0.32} \cdot \frac{0.95}{1 + 0.312} \approx 1.131\text{ pu} = 113.1\text{ MW (100 MVA base)}$$

The minimum receiving-end voltage at the limit is

$$V_{\min} = \frac{1}{\sqrt{2 + 2 \times 0.312}} \approx 0.617\text{ pu}$$

This means that, with a power factor of 0.95, once the receiving-end voltage falls to around 0.62 pu, the system is already very close to the edge of static voltage collapse.

### 9.4 Estimating Voltage Change When a Shunt Capacitor Bank Is Switched

Suppose a 220 kV bus sees a short-circuit capacity of approximately $S_{sc} = 5000$ MVA. A shunt capacitor bank of $\Delta Q_c = 60$ Mvar is switched in.

$$\Delta U\,(\text{pu}) \approx \frac{60}{5000} = 0.012$$

The bus voltage therefore rises by about 1.2%, corresponding to a line-voltage change of roughly

$$\Delta U_{\text{kV}} \approx 2.64\text{ kV}$$

Switching out the same capacitor bank produces the same magnitude in the opposite direction.

### 9.5 Reactive-Power Estimation for a 500 kV Long Transmission Line

Consider a 500 kV long transmission line with natural power $P_N = 1000$ MW, charging power per unit length $Q_N = 1.2$ Mvar/km, and line length $l = 200$ km. Then the charging-power base is

$$Q_N l = 240\text{ Mvar}$$

Under light load, 700 MW:

$$\Delta Q_L = [(0.7)^2 - 1] \times 240 = -122.4\text{ Mvar}$$

so the line generates net reactive power.

Under heavy load, 1400 MW:

$$\Delta Q_L = [(1.4)^2 - 1] \times 240 = +230.4\text{ Mvar}$$

so the line absorbs net reactive power.

The dividing point is precisely the natural power of 1000 MW. Combined with the capacitor-switching estimate in Example 9.4, this immediately indicates whether reactive-compensation devices should be switched in or out under different loading patterns.

### 9.6 Quick Estimation by the Transient-Stability Impact Method

Suppose that during a fault the approximate accelerating power is $\Delta P_a = 0.9$ pu, the clearing time is $\Delta t = 0.12$ s, the maximum transmittable power of the post-fault network is $P_{\max}^{\text{post}} = 1.65$ pu, and $T_j = 9$ s.

The post-fault stable equilibrium angle is

$$\delta_s = \arcsin(0.9/1.65) \approx 33.1^\circ$$

and

$$K_s^{\text{post}} = 1.65\cos 33.1^\circ \approx 1.383$$

The post-fault oscillation frequency is

$$f_d = \frac{1}{2\pi}\sqrt{\frac{314 \times 1.383}{9}} \approx 1.106\text{ Hz}$$

The one-sided swing amplitude is

$$D_p = 2\pi \times 1.106 \times 0.9 \times 0.12 \approx 0.750\text{ pu}$$

Hence the estimated transient-stability limit is

$$P_{st} \approx 1.65 - 0.750 = 0.900\text{ pu}$$

A second-layer check can then be made with the critical-clearing-time formula, taking $\delta_0 = 0.578$ rad:

$$\delta_{cr} = \arccos\!\left[\frac{0.9}{1.65}(\pi - 2 \times 0.578) - \cos 33.1^\circ\right] \approx 75.9^\circ = 1.325\text{ rad}$$

$$t_{cr} = \sqrt{\frac{2 \times 9 \times (1.325 - 0.578)}{314 \times 0.9}} \approx 0.218\text{ s}$$

Compared with the actual clearing time $\Delta t = 0.12$ s, the time margin is about 45%. A more exact check using the equal-area criterion for the same scenario gives a transient-stability limit of about 1.239 pu. The impact method is therefore conservative by about 27%. The conservatism comes from replacing the nonlinear equal-area integration on the power-angle curve by a linearized simple-harmonic approximation of the swing amplitude. Used together, the two quick-estimation methods form a complementary two-layer structure: the impact method gives a direct sense of how dangerous the first swing is, while the critical-clearing-time formula gives an engineering criterion for how far the protection-action time is from the limit.

---

## 10. Boundaries of Applicability and Sources of Error

Approximate formulas are useful precisely because they deliberately discard many details. Knowing where they fail is just as important as knowing the formulas themselves.

**Frequency dynamics.** The single-machine equivalent model is suitable for the first several seconds to a dozen seconds after a disturbance. It is particularly useful for analyzing ROCOF, the frequency nadir, and the dominant role of primary frequency control. Over longer time spans, however, boilers, AGC, tie-line control, load recovery, HVDC control, and other medium- and long-term effects become important, and the error grows noticeably.

**Electromechanical oscillation frequency.** The formula gives the dominant approximation of modal frequency, but it does not directly provide damping ratio or amplitude. If the real question is why an oscillation amplitude grows, or why the damping of an inter-area mode deteriorates, then one must move to eigenvalue analysis, participation-factor analysis, and controller-parameter study.

**Static voltage-stability limit.** The formula is fundamentally a two-bus equivalent result. If the system contains complex reactive compensation, tap-changing action, non-negligible resistance, or strong multi-bus voltage coupling, then the formula should be used only to build intuition and should not replace power-flow, continuation-power-flow, or QV/PV-curve analysis.

**Natural power of transmission lines.** The formula is most suitable for EHV and UHV long lines. For medium or short lines, or lines with series compensation, significant resistance, or complex shunt compensation, the direct use of the natural-power formula becomes noticeably rough.

**Transient-stability formulas.** The impact method is the coarsest approximation. It is suitable for quickly judging whether the first-swing amplitude and transfer level are in a dangerous region. The critical-clearing-time formula is somewhat stricter and more directly answers whether relay action time is adequate. Neither can replace formal transient-stability simulation, but used together they can greatly reduce unnecessary detailed simulations while also avoiding missed identification of obviously dangerous cases.

---

## 11. Concluding Remarks

This paper builds an approximate understanding of power systems at two levels.

The first level is that of **approximate constants**. The current-carrying capacity of a single conductor is confined to 400 to 1000 A, propagation velocity remains close to the speed of light, positive-sequence reactance lies in the range of 0.2 to 0.4 Ω/km, transformer percent short-circuit impedance stays around 4% to 15%, and generator inertia constants fall in the range of 2 to 6 s. The stability of these quantities is not accidental. It is the combined consequence of physical laws and material limits.

The second level is that of **approximate formulas**: the second-order model of frequency dynamics, the formula for electromechanical oscillation frequency, the static voltage-stability limit, quick bus-voltage estimation and capacitor-switching estimation, the natural power of transmission lines and their reactive-power loss, and the transient-stability impact method together with the critical-clearing-time estimate. The value of these formulas does not lie in replacing accurate models, but in exposing the physical mechanisms behind simulation results. They tell us in what direction the system is likely to evolve and which parameters are the most sensitive.

Experienced analysts typically first use approximate formulas to judge order of magnitude, direction, and sensitivity, and then use detailed models to confirm boundaries, correct deviations, and design actual control measures. If one relies on numerical simulation alone and abandons approximate formulas entirely, it becomes easy to lose an intuitive feel for the system.

---

## References

[1] Zhou Rongguang. *A Refined Analysis of Power System Theory* [M]. Publishing House of Electronics Industry, 2014.

[2] Wang Meiyi. *Accident Analysis and Technical Applications in Large Power Grids* [M]. China Electric Power Press, 2008.

[3] Kundur P. *Power System Stability and Control* [M]. China Electric Power Press, 2002.

[4] Electric Power Planning & Engineering Institute, Ministry of Electric Power Industry. *Power System Design Manual* [M]. China Electric Power Press, 1998.
