import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5.QtCore import QThread, pyqtSignal
from taobao import subscribe_live_msg


class AsyncTaskThread(QThread):
    """高性能多线程任务执行器"""

    # 信号
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(dict)  # {'done': 10, 'total': 100, 'success': 8, 'failed': 2}
    finished_signal = pyqtSignal(dict)

    def __init__(self, tasks, max_concurrent=100):
        """
        Args:
            tasks: 任务列表 [{'user': user, 'device': device}, ...]
            max_concurrent: 最大并发数 (建议 50-200)
        """
        super().__init__()
        self.tasks = tasks
        self.max_concurrent = max_concurrent
        self.is_running = True

    def run(self):
        """执行多线程任务"""
        success_count = 0
        fail_count = 0
        completed_count = 0

        self.log_signal.emit(f"🚀 开始执行 {len(self.tasks)} 个任务，并发数={self.max_concurrent}")
        start_time = time.time()

        # 使用线程池执行任务
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            # 提交所有任务
            future_to_index = {}
            for i, task_data in enumerate(self.tasks):
                if not self.is_running:
                    self.log_signal.emit("⏹️ 任务已停止")
                    break

                future = executor.submit(
                    self._execute_single_task,
                    task_data['device'],
                    task_data['user'],
                    task_data['account_id'],
                    task_data['live_id'],
                    task_data['topic'],
                    task_data['proxy']
                )
                future_to_index[future] = i

            # 处理完成的任务
            for future in as_completed(future_to_index):
                if not self.is_running:
                    break

                completed_count += 1
                task_index = future_to_index[future]

                try:
                    success, result = future.result(timeout=30)  # 30秒超时
                    if success:
                        success_count += 1
                        # 检查是否返回了 role=5
                        if isinstance(result, dict) and result.get('role') in [5, '5']:
                            self.log_signal.emit(f"{completed_count}. ✅ 刷量成功 (role=5)")
                        else:
                            self.log_signal.emit(f"{completed_count}. ✔ 任务成功")
                    else:
                        fail_count += 1
                        # 提取失败原因的关键信息
                        error_msg = str(result)
                        if "role=1" in error_msg:
                            self.log_signal.emit(f"{completed_count}. ⚠️ 被识别为异常")
                        elif "robot" in error_msg:
                            self.log_signal.emit(f"{completed_count}. ❌ 设备被封禁")
                        elif "invalid timestamp" in error_msg:
                            self.log_signal.emit(f"{completed_count}. ❌ 时间戳无效")
                        elif "请求超时" in error_msg or "timeout" in error_msg.lower():
                            self.log_signal.emit(f"{completed_count}. ⏱️ 请求超时（代理慢）")
                        elif "代理" in error_msg or "proxy" in error_msg.lower():
                            self.log_signal.emit(f"{completed_count}. 🔌 代理连接失败")
                        elif "算法" in error_msg or "pad block" in error_msg or "Sequence contains" in error_msg:
                            self.log_signal.emit(f"{completed_count}. 🔧 算法服务错误")
                        elif "网络" in error_msg or "connection" in error_msg.lower():
                            self.log_signal.emit(f"{completed_count}. 🌐 网络连接失败")
                        else:
                            self.log_signal.emit(f"{completed_count}. ❌ 失败: {error_msg[:50]}")
                except Exception as e:
                    fail_count += 1
                    self.log_signal.emit(f"{completed_count}. ❌ 任务异常: {str(e)[:50]}")

                # 每完成10个任务报告一次进度 (减少UI更新开销)
                if completed_count % 10 == 0 or completed_count == len(self.tasks):
                    self.progress_signal.emit({
                        'done': completed_count,
                        'total': len(self.tasks),
                        'running': len(self.tasks) - completed_count,
                        'success': success_count,
                        'failed': fail_count
                    })

        # 最终统计
        total_time = time.time() - start_time
        avg_speed = len(self.tasks) / total_time if total_time > 0 else 0

        self.progress_signal.emit({
            'done': len(self.tasks),
            'total': len(self.tasks),
            'running': 0,
            'success': success_count,
            'failed': fail_count
        })

        # 发送完成信号
        self.finished_signal.emit({
            'total': len(self.tasks),
            'success': success_count,
            'failed': fail_count,
            'total_time': total_time,
            'avg_speed': avg_speed
        })

        self.is_running = False
        self.log_signal.emit(
            f"✅ 任务完成! 成功={success_count}, 失败={fail_count}, "
            f"耗时={total_time:.2f}秒, 平均速度={avg_speed:.1f}任务/秒"
        )

    def _execute_single_task(self, device, user, account_id, live_id, topic, proxy):
        """执行单个任务"""
        try:
            return subscribe_live_msg(device, user, account_id, live_id, topic, proxy)
        except Exception as e:
            return False, str(e)

    def stop(self):
        """停止任务"""
        self.is_running = False


# 兼容旧版本的类名
AsyncTaskManager = AsyncTaskThread
