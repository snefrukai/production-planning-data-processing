# AGENTS.md

## 子项目定位

`script/` 是在制分析工具的可运行代码目录，包含 Streamlit 页面、派工进度处理逻辑、测试和输出标准。

## 关键文件

- `app.py`：Streamlit 入口。
- `dispatch_processor.py`：在制分析核心逻辑。
- `models.py`：输出数据结构。
- `utils.py`：文件读取、表头识别、数值清洗。
- `../docs/输出标准.md`：业务输出标准，优先阅读。
- `test/`：自动化测试和本地批处理脚本。
- `input/`：测试输入文件。
- `output/`：批处理输出文件。

## 业务规则入口

- 业务规则以根目录 `docs/输出标准.md` 为准。
- `AGENTS.md` 不复制业务规则，只说明工作约定。
- 需要改业务口径时，先更新 `../docs/输出标准.md`，再同步代码和测试。

## 验证要求

完成代码改动前至少运行：

```powershell
pytest test/ -q
ruff check .
```

如改动了格式或大面积 Python 代码，运行：

```powershell
ruff format .
```

当前环境常用 `uv run --no-project --managed-python --python 3.12 ...` 执行测试和工具。
