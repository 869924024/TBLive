"""
测试代理池管理器
快速验证ProxyManager功能
"""
from proxy_manager import ProxyManager


def test_basic_functions():
    """测试基础功能"""
    print("=" * 60)
    print("🧪 测试代理池管理器基础功能")
    print("=" * 60)
    
    # 快代理API URL（你的真实URL）
    kdl_api_url = "https://dps.kdlapi.com/api/getdps/?secret_id=ozs9u95yw6rq49yg1gfm&signature=nk3a1e0kbg1td6dkjgozokdtprvmt92h&num=2&format=text&sep=1&f_auth=1&generateType=1"
    
    # 创建管理器
    print("\n1️⃣ 创建ProxyManager实例...")
    proxy_manager = ProxyManager(kdl_api_url, tasks_per_ip=30)
    print(f"   ✅ 创建成功，每IP分配: {proxy_manager.tasks_per_ip}")
    
    # 测试计算需求
    print("\n2️⃣ 测试IP需求计算...")
    test_cases = [
        (1000, 3, 1),  # 1000设备 × 3账号 × 1倍
        (500, 2, 2),   # 500设备 × 2账号 × 2倍
        (100, 5, 1),   # 100设备 × 5账号 × 1倍
    ]
    
    for devices, accounts, multiplier in test_cases:
        total_tasks = devices * accounts * multiplier
        required_ips = proxy_manager.calculate_required_ips(total_tasks)
        print(f"   {devices}设备 × {accounts}账号 × {multiplier}倍 = {total_tasks}任务 → 需要 {required_ips} 个IP")
    
    # 测试提取IP（只提取2个进行测试）
    print("\n3️⃣ 测试提取IP (提取2个测试)...")
    proxies = proxy_manager.extract_proxies(2)
    if proxies:
        print(f"   ✅ 成功提取 {len(proxies)} 个IP:")
        for i, proxy in enumerate(proxies, 1):
            ip = proxy.split(':')[0]
            print(f"      {i}. {ip}:****")
    else:
        print("   ❌ 提取失败")
        return False
    
    # 测试IP可用性（快速测试）
    print("\n4️⃣ 测试IP可用性...")
    valid, failed = proxy_manager.test_proxies_batch(proxies, max_workers=2)
    print(f"   可用: {len(valid)}/{len(proxies)}")
    print(f"   失败: {len(failed)}/{len(proxies)}")
    
    # 测试任务分配
    print("\n5️⃣ 测试任务分配逻辑...")
    proxy_manager.proxies = proxies[:2]  # 模拟有2个可用IP
    print(f"   假设有 {len(proxy_manager.proxies)} 个可用IP")
    print(f"   每IP分配: {proxy_manager.tasks_per_ip} 个任务")
    print("\n   任务分配示例:")
    for i in range(90):  # 测试90个任务
        proxy = proxy_manager.get_proxy_for_task(i)
        ip = proxy.split(':')[0] if proxy else "无"
        if i % 30 == 0:  # 每30个任务打印一行
            print(f"      任务 {i:3d}-{i+29:3d} → IP: {ip}")
    
    print("\n" + "=" * 60)
    print("✅ 基础功能测试完成！")
    print("=" * 60)
    return True


def test_full_scenario():
    """测试完整场景（可选，需要真实API）"""
    print("\n" + "=" * 60)
    print("🚀 测试完整初始化场景")
    print("=" * 60)
    
    # 快代理API URL
    kdl_api_url = "https://dps.kdlapi.com/api/getdps/?secret_id=ozs9u95yw6rq49yg1gfm&signature=nk3a1e0kbg1td6dkjgozokdtprvmt92h&num=2&format=text&sep=1&f_auth=1&generateType=1"
    
    # 创建管理器
    proxy_manager = ProxyManager(kdl_api_url, tasks_per_ip=30)
    
    # 模拟场景：10设备 × 3账号 × 1倍 = 30任务
    # 需要 ceil(30/30) = 1个IP
    total_tasks = 10 * 3 * 1
    
    print(f"\n📊 模拟场景:")
    print(f"   设备数: 10")
    print(f"   账号数: 3")
    print(f"   操作倍数: 1")
    print(f"   总任务: {total_tasks}")
    print(f"   每IP分配: {proxy_manager.tasks_per_ip}")
    print(f"   预计需要: {proxy_manager.calculate_required_ips(total_tasks)} 个IP")
    
    print("\n🔄 开始初始化代理池...")
    success = proxy_manager.initialize_proxies(total_tasks, max_retries=1)
    
    if success:
        print("\n✅ 初始化成功！")
        proxy_manager.print_distribution_info()
    else:
        print("\n⚠️ 初始化部分失败")
        print(f"   已获取 {len(proxy_manager.proxies)} 个可用IP")
    
    print("\n" + "=" * 60)
    return success


if __name__ == "__main__":
    import sys
    
    # 测试基础功能
    if not test_basic_functions():
        print("\n❌ 基础功能测试失败")
        sys.exit(1)
    
    # 询问是否测试完整场景
    print("\n" + "=" * 60)
    choice = input("是否测试完整初始化场景？(会实际调用快代理API) [y/N]: ")
    
    if choice.lower() == 'y':
        test_full_scenario()
    else:
        print("跳过完整场景测试")
    
    print("\n🎉 所有测试完成！")

