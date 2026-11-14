# Arthsavora Statistical Anomaly Detection: MAD & IQR Models

## 1. Overview & Statistical Motivation

Financial data distributions are heavily skewed, non-Gaussian, and prone to extreme variance. Standard statistical models (such as Gaussian mean and standard deviation) break down because high-value outliers distort the mean and inflate variance, leading to false negatives (masking real anomalies) and false positives.

Arthsavora utilizes **non-parametric, robust statistical estimators**:
1. **Median Absolute Deviation (MAD)** and **Modified Z-Score** for merchant amount outlier analysis.
2. **Interquartile Range (IQR)** for category volume spike detection.

---

## 2. Robust Merchant Outlier Detection via MAD

### Mathematical Formulation

Given a sample of historical payment amounts at a specific merchant $X = \{x_1, x_2, \dots, x_n\}$:

1. **Median Calculation:**
   $$\tilde{x} = \text{median}(X)$$

2. **Median Absolute Deviation (MAD):**
   $$\text{MAD} = \text{median}\left(\{|x_i - \tilde{x}| : i = 1, \dots, n\}\right)$$

3. **Dispersion Floor Protection:**
   To prevent division by zero or infinite sensitivity when a user always pays an exact recurring amount (e.g. exactly ₹199 each time):
   $$\text{MAD}_{\text{eff}} = \max\left(\text{MAD}, 0.15 \times \tilde{x}, 10000.0\text{ paise}\right)$$

4. **Modified Z-Score ($M_i$):**
   Based on Boris Iglewicz and David Hoaglin (1993):
   $$M_i = \frac{0.6745 \times (x_{\text{candidate}} - \tilde{x})}{\text{MAD}_{\text{eff}}}$$
   The constant $0.6745$ equates the expectation to standard deviation under a normal distribution.

5. **Decision Boundary:**
   - **$M_i \ge 3.5$**: Classified as a statistically significant merchant outlier.
   - **$M_i \ge 5.0$**: Escalated to `HIGH` severity.
   - **Sample Size Requirement:** Requires at least $n \ge 5$ historical observations to avoid false alarms on sparse histories.

---

## 3. Category Spending Spike Detection via IQR

### Mathematical Formulation

For monthly category expenditure monitoring:
1. Historical daily spending samples $D = \{d_1, d_2, \dots, d_m\}$ over the trailing 90 days.
2. Interquartile Range:
   $$\text{IQR} = Q_3 - Q_1$$
   where $Q_1$ is the 25th percentile and $Q_3$ is the 75th percentile.
3. Upper Baseline Expectation:
   $$\text{Upper Threshold} = Q_3 + 2.5 \times \text{IQR}$$
   Expected Monthly Volume: $\text{Base}_{\text{monthly}} = \text{Upper Threshold} \times 30.4375$.
4. **Spike Ratio:**
   $$\text{Ratio} = \frac{\text{Current Month Spend}}{\max(\text{Base}_{\text{monthly}}, 1.0)}$$
5. **Decision Boundary:**
   If $\text{Ratio} \ge 2.5$ and current monthly spend $\ge$ ₹15,000, an anomaly is flagged with `category` classification.
