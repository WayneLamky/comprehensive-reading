# 示例源文本（虚构，仅用于演示规格；不是任何真实项目的材料）

> 这份「研究计划摘录」是为了演示 comprehensive-reading 的「主张—依据—边界」模式而编写的，段落编号 ¶1–¶6 用作锚点。

¶1 Background. Automated image analysis is increasingly used to judge the quality of cultured cells before they are released for use. Most published pipelines, however, report performance only on cells from the same donors that were used for training.

¶2 Gap. Without an evaluation on donors the model has never seen, it is unclear whether such pipelines measure a property of the cells or a property of the donor.

¶3 Aim. This project will test whether a label-free morphology model trained on cells from a set of donors keeps its accuracy on cells from new donors.

¶4 Design. Cells from twelve donors will be imaged on days 1–4 of expansion. The model will be trained on eight donors and tested on the remaining four. No image from a test donor will be used during training or model selection.

¶5 Expected outcome. If accuracy on the four held-out donors stays within ten percentage points of the training-donor accuracy, the model will be considered donor-transferable.

¶6 Limitations. Twelve donors are few; a result on four held-out donors cannot establish transfer to the whole patient population, and the project does not test cells from diseased donors.
