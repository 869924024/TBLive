"""
快代理IP池管理器
自动提取、测试、分配IP代理
"""
from urllib.parse import urlunparse, urlencode, parse_qs, urlparse

import requests
import time
import threading
from typing import List, Dict, Tuple
import math

# 尝试导入loguru，如果失败则使用print
try:
    from loguru import logger
except ImportError:
    class SimpleLogger:
        def info(self, msg): print(f"[INFO] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
        def warning(self, msg): print(f"[WARN] {msg}")
        def debug(self, msg): pass  # debug信息不打印
    logger = SimpleLogger()


class ProxyManager:
    """代理IP管理器"""
    
    def __init__(self, kdl_api_url: str, tasks_per_ip: int = 30):
        """
        初始化代理管理器
        
        Args:
            kdl_api_url: 快代理API URL
            tasks_per_ip: 每个IP分配的任务数（默认30）
        """
        self.kdl_api_url = kdl_api_url
        self.tasks_per_ip = tasks_per_ip
        self.proxies: List[str] = []  # 可用的代理列表
        self.proxy_lock = threading.Lock()
        
    def calculate_required_ips(self, total_tasks: int) -> int:
        """
        计算需要的IP数量
        
        Args:
            total_tasks: 总任务数（设备数 × 账号数 × 操作倍数）
            
        Returns:
            需要的IP数量
        """
        # 向上取整
        required = math.ceil(total_tasks / self.tasks_per_ip)
        logger.info(f"📊 总任务数: {total_tasks}, 每IP分配: {self.tasks_per_ip}, 需要IP: {required}个")
        return required

    def extract_proxies(self, num: int) -> List[str]:
        """
        从快代理提取IP

        Args:
            num: 要提取的IP数量

        Returns:
            IP列表，格式: ["IP:PORT:USER:PASS", ...]
        """
        try:
            # 解析URL并更新num参数
            parsed_url = urlparse(self.kdl_api_url)
            query_params = parse_qs(parsed_url.query)
            query_params['num'] = [str(num)]  # 更新或添加num参数
            new_query = urlencode(query_params, doseq=True)
            url = urlunparse(parsed_url._replace(query=new_query))

            logger.info(f"🔌 正在从快代理提取 {num} 个IP...")
            response = requests.get(url, timeout=10)

            if response.status_code != 200:
                logger.error(f"❌ 提取IP失败: HTTP {response.status_code}")
                return []

            # 解析返回的IP列表（格式：IP:PORT:USER:PASS，每行一个）
            text = response.text.strip()
            if not text:
                logger.error("❌ 提取IP失败: 返回为空")
                return []

            proxies = [line.strip() for line in text.split('\n') if line.strip()]
            logger.info(f"✅ 成功提取 {len(proxies)} 个IP")
            return proxies

        except Exception as e:
            logger.error(f"❌ 提取IP异常: {e}")
            return []
    
    def test_proxy(self, proxy: str, test_url: str = "https://www.taobao.com") -> bool:
        """
        测试单个代理是否可用
        
        Args:
            proxy: 代理字符串 "IP:PORT:USER:PASS"
            test_url: 测试URL
            
        Returns:
            是否可用
        """
        try:
            # 解析代理格式
            parts = proxy.split(':')
            if len(parts) != 4:
                logger.warning(f"⚠️ 代理格式错误: {proxy}")
                return False
            
            ip, port, username, password = parts
            proxy_url = f'http://{username}:{password}@{ip}:{port}'
            
            # 测试连接（3秒超时）
            response = requests.get(
                test_url,
                proxies={'http': proxy_url, 'https': proxy_url},
                timeout=3
            )
            
            if response.status_code == 200:
                return True
            else:
                logger.warning(f"⚠️ 代理响应异常 [{ip}:{port}]: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            logger.warning(f"⚠️ 代理超时 [{proxy.split(':')[0]}]")
            return False
        except Exception as e:
            logger.warning(f"⚠️ 代理测试失败 [{proxy.split(':')[0]}]: {str(e)[:50]}")
            return False
    
    def test_proxies_batch(self, proxies: List[str], max_workers: int = 10) -> Tuple[List[str], List[str]]:
        """
        批量测试代理（多线程）
        
        Args:
            proxies: 代理列表
            max_workers: 最大并发线程数
            
        Returns:
            (可用代理列表, 失败代理列表)
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        valid_proxies = []
        failed_proxies = []
        
        logger.info(f"🧪 开始测试 {len(proxies)} 个代理...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有测试任务
            future_to_proxy = {executor.submit(self.test_proxy, proxy): proxy for proxy in proxies}
            
            # 收集结果
            for future in as_completed(future_to_proxy):
                proxy = future_to_proxy[future]
                try:
                    is_valid = future.result()
                    if is_valid:
                        valid_proxies.append(proxy)
                        logger.debug(f"✅ 代理可用: {proxy.split(':')[0]}")
                    else:
                        failed_proxies.append(proxy)
                except Exception as e:
                    logger.warning(f"⚠️ 测试异常 [{proxy.split(':')[0]}]: {e}")
                    failed_proxies.append(proxy)
        
        logger.info(f"✅ 测试完成: 可用 {len(valid_proxies)}/{len(proxies)}, 失败 {len(failed_proxies)}")
        return valid_proxies, failed_proxies
    
    def initialize_proxies(self, total_tasks: int, max_retries: int = 3) -> bool:
        """
        初始化代理池（自动提取并测试）
        
        Args:
            total_tasks: 总任务数
            max_retries: 最大重试次数
            
        Returns:
            是否成功
        """
        # 计算需要的IP数量
        required_ips = self.calculate_required_ips(total_tasks)
        
        # 提取IP并测试，失败则重新提取
        retry_count = 0
        valid_proxies = []
        
        while len(valid_proxies) < required_ips and retry_count < max_retries:
            # 计算还需要多少IP
            need_count = required_ips - len(valid_proxies)
            
            # 第一次提取全部，后续只提取缺失的
            extract_count = required_ips if retry_count == 0 else need_count
            
            logger.info(f"🔄 第 {retry_count + 1} 次提取 (需要 {need_count} 个)...")
            
            # 提取IP
            new_proxies = self.extract_proxies(extract_count)
            if not new_proxies:
                logger.error(f"❌ 第 {retry_count + 1} 次提取失败")
                retry_count += 1
                time.sleep(2)  # 等待2秒后重试
                continue
            
            # 测试IP
            valid_batch, failed_batch = self.test_proxies_batch(new_proxies)
            valid_proxies.extend(valid_batch)
            
            # 如果还有失败的，记录下来
            if failed_batch:
                logger.warning(f"⚠️ 本次有 {len(failed_batch)} 个IP不可用")
            
            retry_count += 1
        
        # 检查是否成功
        if len(valid_proxies) >= required_ips:
            self.proxies = valid_proxies[:required_ips]  # 只取需要的数量
            logger.info(f"✅ 代理池初始化成功！共 {len(self.proxies)} 个可用IP")
            return True
        else:
            logger.error(f"❌ 代理池初始化失败！只获取到 {len(valid_proxies)}/{required_ips} 个可用IP")
            self.proxies = valid_proxies  # 保存所有可用的
            return False
    
    def get_proxy_for_task(self, task_index: int) -> str:
        """
        根据任务索引获取对应的代理
        
        Args:
            task_index: 任务索引（0开始）
            
        Returns:
            代理字符串 "IP:PORT:USER:PASS"
        """
        if not self.proxies:
            logger.warning("⚠️ 代理池为空")
            return ""
        
        # 计算应该使用哪个代理
        proxy_index = task_index // self.tasks_per_ip
        proxy_index = proxy_index % len(self.proxies)  # 循环使用
        
        return self.proxies[proxy_index]
    
    def get_proxy_distribution(self) -> Dict[str, int]:
        """
        获取代理分配统计
        
        Returns:
            {代理IP: 分配任务数}
        """
        distribution = {}
        for i, proxy in enumerate(self.proxies):
            ip = proxy.split(':')[0]
            distribution[ip] = self.tasks_per_ip
        return distribution
    
    def print_distribution_info(self):
        """打印代理分配信息"""
        print("=" * 60)
        print("📊 代理分配统计")
        print("=" * 60)
        print(f"总代理数: {len(self.proxies)}")
        print(f"每IP任务数: {self.tasks_per_ip}")
        print(f"总任务容量: {len(self.proxies) * self.tasks_per_ip}")
        print("-" * 60)
        
        distribution = self.get_proxy_distribution()
        for i, (ip, count) in enumerate(distribution.items(), 1):
            print(f"{i:3d}. {ip:15s} → {count:3d} 任务")
        print("=" * 60)


# 使用示例
if __name__ == "__main__":
    # 快代理API URL
    kdl_api_url = "https://dps.kdlapi.com/api/getdps/?secret_id=ozs9u95yw6rq49yg1gfm&signature=nk3a1e0kbg1td6dkjgozokdtprvmt92h&num=2&format=text&sep=1&f_auth=1&generateType=1"
    
    # 创建代理管理器（每个IP分配30个任务）
    proxy_manager = ProxyManager(kdl_api_url, tasks_per_ip=30)
    
    # 模拟场景：1000设备 × 3账号 × 1倍数 = 3000任务
    total_tasks = 1000 * 3 * 1
    
    # 初始化代理池
    if proxy_manager.initialize_proxies(total_tasks):
        # 打印分配信息
        proxy_manager.print_distribution_info()
        
        # 测试：获取前10个任务的代理
        print("\n" + "=" * 60)
        print("🔍 任务代理分配示例（前30个任务）")
        print("=" * 60)
        for i in range(30):
            proxy = proxy_manager.get_proxy_for_task(i)
            ip = proxy.split(':')[0] if proxy else "无代理"
            print(f"任务 {i:3d} → {ip}")
        print("=" * 60)
    else:
        print("❌ 代理池初始化失败！")

