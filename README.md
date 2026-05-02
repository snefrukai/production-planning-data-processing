# 零件库存跟踪脚本

本目录提供 Streamlit 在制分析工具，用于处理《派工进度追踪表》，输出每个产品型号的在制情况。

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

## 功能模块

### 1. 在制分析

- 上传《派工进度追踪表》（支持 CSV/Excel）
- 自动识别多行列头
- 按产品型号汇总不同派工主题
- 展示在制分析结果，并支持下载 CSV 和 XLSX 报表

### 2. 库存分析

- 规划中：用于对比在制、库存和客户需求。

## 代码结构说明

- `app.py`: Streamlit 前端主入口。
- `dispatch_processor.py`: 派工进度核心业务逻辑。
- `utils.py`: 公共可复用函数（文件读取、清洗、表头检测）。
- `test/`: 自动化测试目录（包含测试数据与 `test_*.py` 用例）。
- `../docs/输出标准.md`: 在制分析业务输出标准，Streamlit 页面底部会展示。
