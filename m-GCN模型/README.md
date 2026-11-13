# GCN布局预测研究

- [多粒度GCN训练思路](多粒度GCN训练思路.md)：记录房间级与功能空间／功能区级数据共同训练的方向、监督边界和验证方法。
- [room_layout_pilot](room_layout_pilot/README.md)：已有09号体检区同图拟合小试验，尚未实现或验证多粒度联合训练。
- [training_data_prep](training_data_prep/README.md)：53图概念边界适配及统一尺度、掩码的布局训练数据导出。
- [relation_prediction](relation_prediction/README.md)为53图access关系评分基线试跑入口，已完成120轮探索训练并保存权重及逐图结果。当前研究阶段与后续模型验证工作见[实际记录](../w-论文正文/GCN_train/03_53图首轮关系训练.md)。

研究目标与数据粒度以思路记录为准；是否采用双模式输出或层级生成，待具体实验方案明确。
