# 示例源文本（虚构的小型研究摘要，仅用于演示「study」模式；不是任何已发表论文）

> 段落编号 ¶1–¶5 与 Figure 1 用作锚点。Figure 1 是本仓库自绘的 SVG 示意图（figure-1.svg），不是任何论文的原图。

¶1 Question. We asked whether the average cell area measured on day 2 of expansion predicts the population doubling time (PDT) measured over the following week.

¶2 Samples. Cells from three donors (A, B, C) were each cultured in four wells, giving twelve wells. One phase-contrast image per well was taken on day 2.

¶3 Measurements. Average cell area per well was computed from the day-2 image (input). PDT per well was calculated from cell counts on day 2 and day 9 (target).

¶4 Analysis. A linear regression of PDT on average area was fitted. Leave-one-well-out cross-validation gave a mean absolute error of 4.1 h; the null model (always predict the mean PDT) gave 7.9 h.

¶5 Interpretation. Day-2 average area carries information about the following week's growth in these three donors. Because wells from the same donor appear in both training and test folds, the result does not show that the model transfers to a new donor.

Figure 1. Scatter of average cell area (x axis, µm²) against PDT (y axis, h) for the twelve wells; symbols coded by donor. A fitted line is shown.
