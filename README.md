# 生产计划数据分析系统

Web 应用：基于多页签的设计，用于工厂现场的生产进度分析和库存分析。

## 环境和运行

需要安装 Python 3.8+。

```bash
cd script
```

**安装依赖**

```bash
pip install -r requirements.txt
```

**运行 Streamlit Web 界面**

```bash
streamlit run app.py
```

**本地批量处理命令行** (测试并处理 `script/input/` 中的文件)

```bash
python test/run_test.py
```

**运行自动化测试** (请确保安装了 pytest)

```bash
pytest test/ -v
```

## 功能模块 (Tabs)

### 1. 派工进度分析

- 上传《派工进度追踪表》（支持 CSV/Excel）
- 自动识别多行列头
- 计算各零件在各工艺路线工序中的**待处理量**
- 展示处理结果，并支持下载修正过的 CSV 和 XLSX 报表

### 2. 库存分析

- _(规划中：用于对比派工加工需求与当前库存的差异，制定后续生产计划。)_

## 代码结构说明

- `app.py`: Streamlit 前端主入口。
- `dispatch_processor.py`: 派工进度核心业务逻辑。
- `utils.py`: 公共可复用函数（文件读取、清洗、表头检测）。
- `test/`: 自动化测试目录（包含测试数据与 `test_*.py` 用例）。
- `prompt.md`: 业务处理逻辑的纯文本规范文档，支持系统内查阅。
