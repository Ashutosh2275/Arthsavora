# Arthsavora Machine Learning Anomaly Detection: Isolation Forest

## 1. Overview & Theoretical Basis

While deterministic rules and 1D statistical models detect single-variable deviations (e.g., amount or frequency), sophisticated financial anomalies occur across **multivariate correlations** (e.g., an unusual amount transacted at an unusual hour with an unprecedented time delta between payments).

Arthsavora deploys **Isolation Forest (Liu, Ting, and Zhou, 2008)**, an unsupervised tree-based ensemble method that explicitly isolates anomalies instead of profiling normal data points.

---

## 2. Model Mechanics

### Principle of Isolation
- Anomalous data points have extreme values or sparse neighborhoods in feature space.
- In randomized binary partitioning trees ($iTrees$), anomalies require fewer random recursive cuts to become isolated in terminal leaf nodes.
- Path length $h(x)$ from root to terminal leaf inversely correlates with anomaly likelihood.

### Anomaly Score Formulation

The normalized anomaly score $s(x, n)$ for sample $x$ over $n$ training instances is defined as:

$$s(x, n) = 2^{-\frac{\mathbb{E}(h(x))}{c(n)}}$$

where $c(n)$ is the average path length of unsuccessful searches in a Binary Search Tree (BST):

$$c(n) = 2 \ln(n - 1) + 0.5772156649\text{ (Euler's constant)} - \frac{2(n - 1)}{n}$$

- If $\mathbb{E}(h(x)) \to 0 \implies s \to 1$: Highly anomalous.
- If $\mathbb{E}(h(x)) \to n - 1 \implies s \to 0$: Distinctly normal.
- If $\mathbb{E}(h(x)) \to c(n) \implies s \to 0.5$: Indeterminate.

---

## 3. Implementation in Arthsavora

### Dynamic Batch Fit & Candidate Evaluation
```python
X_train = np.array(historical_feature_matrix, dtype=np.float64)
X_cand = np.array([candidate_features], dtype=np.float64)
X_all = np.vstack([X_train, X_cand])

clf = IsolationForest(
    n_estimators=100,
    contamination=0.03,  # Target top 3% extreme multivariate outliers
    random_state=42,
    n_jobs=1,
)
clf.fit(X_all)

pred = clf.predict(X_cand)[0]            # -1 for outlier, 1 for inlier
decision_score = float(clf.decision_function(X_cand)[0])
```

### Cold-Start Guardrail
- The model enforces a minimum training sample size:
  $$\text{Sample Count} \ge 30\text{ historical transactions}$$
- If fewer than 30 transactions exist in the tenant workspace, ML inference gracefully returns `None`, and the system relies exclusively on deterministic rules and statistical MAD.
