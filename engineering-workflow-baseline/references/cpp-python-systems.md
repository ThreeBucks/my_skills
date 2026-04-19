# C++/Python 系统仓库工作手册

## 常见仓库形态

- 根目录有 `CMakeLists.txt` 和 `scripts/` 作为构建或环境入口
- C++ 实现在 `ccl/`、`core/`、`operators/`、`ops_impl/` 这类目录下
- Python 绑定或测试在 `python/`、`test/py_test/` 一类目录下
- 公开头文件、实现、测试和文档之间通常需要保持一致

## AdaDnn 场景提示

### 常用构建命令

```bash
bash scripts/install_dependencies.sh
source scripts/env.sh
bash scripts/build_project.sh enable_test
cd build && ninja install
```

### 常用测试命令

```bash
./build/test/test-ada-dnn
./build/test/test-ada-ccl --gtest_filter="AdaTest/GatherTests.gather/*"
pytest test/py_test/ccl -s --tb=short --timeout=60
```

### 常见运行时与集群环境变量

- `ADAX_RT_USE_TSIM_MODE`
- `TSIM_LITE_THREADS`
- `ADAX_TSIM_WITH_HACK_PRINTF`
- `ADAVM_CLIENT_PATH`
- `SIM_LOG_MIN_LEVEL`
- `CCL_FORK_TEST`

## CCL 或 P2P 变更的风险清单

- 发送端和接收端契约是否一致
- shape、count、dtype、rank 假设是否在整条链路上保持一致
- 初始化顺序和 world-size 假设是否正确
- 公开头文件、实现和测试是否同步演进
- 异常路径、不支持场景和报错语义是否仍然自洽

## 建议的首轮排查命令

```bash
pwd
git status --short
rg --files ccl test python core | sed -n '1,120p'
rg -n "symbol_or_api_name" ccl test python core
```
