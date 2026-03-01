# 自动化测试说明

本目录包含对数据处理逻辑的单元测试和集成测试。

## 测试框架

- **框架**: `pytest`
- **目的**: 保证代码重构和后续新增功能时，核心的【派工进度】数据处理逻辑和【公共工具类】不被破坏。

## 目录结构

```text
test/
├── input/                  # 测试用的输入文件（.csv, .xls, .xlsx）
├── test_processor.py       # 派工业务逻辑集成测试（依赖 input 文件夹内文件）
├── test_utils.py           # 公共函数测试（读取文件、清理数据、表头检测等）
└── run_test.py             # 辅助脚本：提供控制台可视化的批量文件执行和预览。结果会输出到上级目录的 `output/` 中。
```

## 如何运行测试

在命令行中（确保位于项目 `script` 目录下），运行：

```bash
# 运行所有测试用例，并显示详细信息
pytest test/ -v

# 只运行特定模块的测试
pytest test/test_utils.py -v
pytest test/test_processor.py -v
```

## 编写新测试

- **新增测试类/函数**：需以 `Test` 开头的类名，或以 `test_` 开头的函数名。
- **公共工具测试**：写在 `test_utils.py`。
- **业务逻辑测试**：写在 `test_processor.py`。如需使用新的测试文件，请将其放入 `input/` 文件夹并作为测试桩供代码调用。
