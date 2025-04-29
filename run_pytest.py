#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
使用pytest运行所有测试的脚本
"""

import sys
import pytest

def run_all_tests():
    """运行所有测试"""
    # 运行单元测试和集成测试，但不包括手动测试
    args = ["-v", "-m", "not manual", "tests"]
    
    # 运行测试并返回结果
    return pytest.main(args)

def run_unit_tests():
    """只运行单元测试"""
    args = ["-v", "-m", "unit", "tests"]
    return pytest.main(args)

def run_integration_tests():
    """只运行集成测试"""
    args = ["-v", "-m", "integration", "tests"]
    return pytest.main(args)

def run_manual_tests():
    """运行手动测试（需要启动服务器）"""
    args = ["-v", "-m", "manual", "tests"]
    return pytest.main(args)

if __name__ == "__main__":
    # 解析命令行参数
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        if test_type == "unit":
            exit_code = run_unit_tests()
        elif test_type == "integration":
            exit_code = run_integration_tests()
        elif test_type == "manual":
            exit_code = run_manual_tests()
        else:
            print(f"未知的测试类型: {test_type}")
            print("可用选项: unit, integration, manual")
            exit_code = 1
    else:
        # 默认运行所有自动测试
        exit_code = run_all_tests()
    
    # 设置退出码
    sys.exit(exit_code)
