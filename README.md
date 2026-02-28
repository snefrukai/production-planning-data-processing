# 派工进度追踪表处理

Web应用：根据派工进度追踪表，计算零件未入库情况。

## 运行

```bash
cd script
pip install -r requirements.txt
streamlit run app.py
```

## 功能

- 上传 CSV/Excel 派工数据
- 多行列头自动识别
- 计算各工序待处理量
- 输出 CSV 下载
