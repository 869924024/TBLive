#!/usr/bin/env python3
"""
速度测试脚本 - 验证性能优化效果
"""

import time
import sys
import os
from model.user import User
from model.device import Device
from task_batch import AsyncTaskThread


def create_test_data(count=50):
    """创建测试数据"""
    tasks = []
    for i in range(count):
        user = User(
            uid=f"test_user_{i}",
            nickname=f"测试用户{i}",
            sid=f"test_sid_{i}",
            cookies=f"test_cookie_{i}"
        )
        device = Device(
            utdid=f"test_device_{i}",
            umt=f"test_umt_{i}",
            devid=f"test_devid_{i}",
            miniwua=f"test_miniwua_{i}",
            sgext=f"test_sgext_{i}",
            ttid=f"test_ttid_{i}"
        )
        task = {
            'user': user,
            'device': device,
            'account_id': f"account_{i}",
            'live_id': f"live_{i}",
            'topic': f"topic_{i}",
            'proxy': ""  # 不使用代理测试
        }
        tasks.append(task)
    return tasks


def run_speed_test():
    """运行速度测试"""
    print("=" * 50)
    print("🚀 速度测试 - 验证优化效果")
    print("=" * 50)

    from PyQt5.QtWidgets import QApplication

    # 创建Qt应用
    app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()

    # 测试不同规模
    test_cases = [
        {"count": 10, "concurrent": 10, "name": "小规模测试"},
        {"count": 50, "concurrent": 25, "name": "中等规模测试"},
        {"count": 100, "concurrent": 50, "name": "大规模测试"},
    ]

    for test_case in test_cases:
        print(f"\n📊 {test_case['name']}: {test_case['count']} 个任务")
        print("-" * 30)

        # 创建测试数据
        tasks = create_test_data(test_case['count'])

        # 创建任务线程
        task_thread = AsyncTaskThread(
            tasks=tasks,
            max_concurrent=test_case['concurrent']
        )

        # 连接信号
        def on_log(msg):
            print(f"[日志] {msg}")

        def on_progress(progress):
            if progress['done'] % 10 == 0 or progress['done'] == progress['total']:
                print(f"进度: {progress['done']}/{progress['total']} "
                      f"成功: {progress['success']} 失败: {progress['failed']}")

        def on_finished(result):
            print(f"\n✅ 测试完成!")
            print(f"总数: {result['total']}")
            print(f"成功: {result['success']}")
            print(f"失败: {result['failed']}")
            if 'avg_speed' in result:
                print(f"平均速度: {result['avg_speed']:.2f} 任务/秒")
            if 'total_time' in result:
                print(f"总耗时: {result['total_time']:.2f} 秒")

        task_thread.log_signal.connect(on_log)
        task_thread.progress_signal.connect(on_progress)
        task_thread.finished_signal.connect(on_finished)

        # 执行测试
        start_time = time.time()
        task_thread.start()

        # 等待完成
        while task_thread.isRunning():
            app.processEvents()
            time.sleep(0.1)

        actual_time = time.time() - start_time
        print(f"实际总耗时: {actual_time:.2f} 秒")

        # 计算性能指标
        if actual_time > 0:
            speed = test_case['count'] / actual_time
            print(f"实际速度: {speed:.2f} 任务/秒")

        print("-" * 30)


def check_dependencies():
    """检查依赖"""
    print("🔍 检查依赖...")

    try:
        import requests
        print("✅ requests 已安装")
    except ImportError:
        print("❌ requests 未安装，请运行: pip install requests")
        return False

    try:
        from PyQt5.QtWidgets import QApplication
        print("✅ PyQt5 已安装")
    except ImportError:
        print("❌ PyQt5 未安装，请运行: pip install PyQt5")
        return False

    # 检查签名服务
    try:
        import requests
        resp = requests.get("http://localhost:9001", timeout=2)
        print("✅ 签名服务运行正常")
    except:
        print("⚠️  签名服务 (localhost:9001) 未运行，测试可能会失败")
        print("请确保签名服务正在运行")

    return True


def main():
    """主函数"""
    print("🎯 淘宝任务执行速度测试")
    print("⚠️  这是测试脚本，使用模拟数据")

    if not check_dependencies():
        print("\n❌ 依赖检查失败，请先安装必要的依赖")
        return

    try:
        run_speed_test()
        print("\n✅ 所有测试完成")
    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试异常: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()