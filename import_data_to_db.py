"""
数据导入辅助脚本
将本地的 账号.txt 和 设备.txt 导入到MySQL数据库
"""

import pymysql
import re
import sys
import math
from concurrent.futures import ThreadPoolExecutor, as_completed


# ============================================
# 数据库配置（修改为你的配置）
# ============================================
DB_CONFIG = {
    'host': '194.41.36.221',
    'port': 3306,
    'user': 'tb_live',
    'password': 'hjj2819597',  # 修改为你的数据库密码
    'database': 'tb_live',         # 修改为你的数据库名
    'charset': 'utf8mb4'
}


def extract_uid_from_cookie(cookie):
    """从Cookie中提取UID"""
    # 尝试提取 unb= 后面的数字
    match = re.search(r'unb=(\d+)', cookie)
    if match:
        return match.group(1)
    return None


def _run_batch_insert(insert_sql: str, params_batch: list[tuple]) -> tuple[int, int]:
    """在独立连接中执行一批插入，返回(成功数, 跳过数)"""
    conn = None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        conn.autocommit(False)
        affected = cursor.executemany(insert_sql, params_batch)
        conn.commit()
        return affected, len(params_batch) - affected
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        print(f"  ⚠️ 批量执行失败: {str(e)[:200]}")
        return 0, len(params_batch)
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def _parallel_bulk_insert(params: list[tuple], insert_sql: str, batch_size: int = 500, max_workers: int = 8, label: str = "进度") -> tuple[int, int]:
    """并发批量插入工具。返回(成功数, 跳过数)。"""
    if not params:
        return 0, 0
    # 切批
    batches = []
    for i in range(0, len(params), batch_size):
        batches.append(params[i:i + batch_size])
    total_batches = len(batches)
    print(f"  {label}: 已启动并发导入 — 共 {total_batches} 批，每批 {batch_size}，线程 {max_workers}", flush=True)
    done_batches = 0
    success_total = 0
    skip_total = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_run_batch_insert, insert_sql, b) for b in batches]
        for fut in as_completed(futures):
            ok, skip = fut.result()
            done_batches += 1
            success_total += ok
            skip_total += skip
            processed = min(done_batches * batch_size, len(params))
            print(f"  {label}: 批次 {done_batches}/{total_batches} | 行 {processed}/{len(params)}", flush=True)
    return success_total, skip_total


def _sequential_bulk_insert_devices(params: list[tuple], client_id, batch_size: int = 1000, label: str = "进度") -> tuple[int, int]:
    """设备批量插入（临时表 + 去重），返回(成功数, 跳过数)。"""
    if not params:
        return 0, 0
    conn = None
    success_total = 0
    skip_total = 0
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        conn.autocommit(False)

        total = len(params)
        total_batches = (total + batch_size - 1) // batch_size
        print(f"  {label}: 单线程批量导入 — 共 {total_batches} 批，每批 {batch_size}", flush=True)

        # 创建临时表（会话级，自动销毁）
        cursor.execute("""
            CREATE TEMPORARY TABLE tmp_devices (
                client_id INT,
                devid VARCHAR(64),
                miniwua VARCHAR(2000),
                sgext VARCHAR(2000),
                umt VARCHAR(2000),
                utdid VARCHAR(100),
                status TINYINT DEFAULT 1,
                INDEX idx_devid (devid)
            ) ENGINE=InnoDB
        """)
        conn.commit()

        for batch_index in range(total_batches):
            start = batch_index * batch_size
            end = min(start + batch_size, total)
            batch = params[start:end]
            try:
                # 先批量插入临时表
                cursor.executemany(
                    "INSERT INTO tmp_devices (client_id, devid, miniwua, sgext, umt, utdid, status) VALUES (%s, %s, %s, %s, %s, %s, 1)",
                    batch
                )
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"  ⚠️ 批 {batch_index+1}/{total_batches} 失败: {str(e)[:200]}")
            processed = end
            print(f"  {label}: 批次 {batch_index+1}/{total_batches} | 行 {processed}/{total}", flush=True)

        # 一次性从临时表插入目标表（去重）
        cursor.execute("""
            INSERT INTO tb_devices (client_id, devid, miniwua, sgext, umt, utdid, status)
            SELECT t.client_id, t.devid, t.miniwua, t.sgext, t.umt, t.utdid, t.status
            FROM tmp_devices t
            LEFT JOIN tb_devices d ON t.devid = d.devid
            WHERE d.id IS NULL
        """)
        success_total = cursor.rowcount
        skip_total = total - success_total
        conn.commit()
        print(f"  {label}: 去重合并完成，成功={success_total}，跳过={skip_total}", flush=True)

        return success_total, skip_total
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def _sequential_bulk_insert_cookies(params: list[tuple], client_id, batch_size: int = 1000, label: str = "进度") -> tuple[int, int]:
    """Cookie批量插入（临时表 + 去重），返回(成功数, 跳过数)。"""
    if not params:
        return 0, 0
    conn = None
    success_total = 0
    skip_total = 0
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        conn.autocommit(False)

        total = len(params)
        total_batches = (total + batch_size - 1) // batch_size
        print(f"  {label}: 单线程批量导入 — 共 {total_batches} 批，每批 {batch_size}", flush=True)

        # 创建临时表
        cursor.execute("""
            CREATE TEMPORARY TABLE tmp_cookies (
                client_id INT,
                cookie VARCHAR(5000),
                uid VARCHAR(64),
                status TINYINT DEFAULT 1,
                INDEX idx_cookie (cookie(100))
            ) ENGINE=InnoDB
        """)
        conn.commit()

        for batch_index in range(total_batches):
            start = batch_index * batch_size
            end = min(start + batch_size, total)
            batch = params[start:end]
            try:
                cursor.executemany(
                    "INSERT INTO tmp_cookies (client_id, cookie, uid, status) VALUES (%s, %s, %s, 1)",
                    batch
                )
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"  ⚠️ 批 {batch_index+1}/{total_batches} 失败: {str(e)[:200]}")
            processed = end
            print(f"  {label}: 批次 {batch_index+1}/{total_batches} | 行 {processed}/{total}", flush=True)

        # 一次性从临时表插入目标表（去重）
        cursor.execute("""
            INSERT INTO tb_cookies (client_id, cookie, uid, status)
            SELECT t.client_id, t.cookie, t.uid, t.status
            FROM tmp_cookies t
            LEFT JOIN tb_cookies c ON t.cookie = c.cookie
            WHERE c.id IS NULL
        """)
        success_total = cursor.rowcount
        skip_total = total - success_total
        conn.commit()
        print(f"  {label}: 去重合并完成，成功={success_total}，跳过={skip_total}", flush=True)

        return success_total, skip_total
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def import_cookies_from_file(file_path='账号.txt', client_id=None):
    """
    从文件导入Cookie到数据库
    
    Args:
        file_path: Cookie文件路径
        client_id: 分配给哪个客户端（None=不分配）
    """
    print(f"\n{'='*60}")
    print(f"📥 正在导入Cookie: {file_path}")
    print(f"{'='*60}")
    
    try:
        # 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"✅ 读取到 {len(lines)} 行数据")
        
        # 预解析参数
        params = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if '----' in line:
                parts = line.split('----', 1)
                if len(parts) == 2:
                    uid, cookie = parts[0].strip(), parts[1].strip()
                else:
                    cookie = line
                    uid = extract_uid_from_cookie(cookie)
            else:
                cookie = line
                uid = extract_uid_from_cookie(cookie)
            params.append((client_id, cookie, uid))

        # 单线程批量导入（临时表 + 去重）
        success_count, skip_count = _sequential_bulk_insert_cookies(params, client_id, batch_size=1000, label="Cookie 进度")
        
        print(f"\n✅ 导入完成:")
        print(f"  - 成功: {success_count} 个")
        print(f"  - 跳过(重复): {skip_count} 个")
        
        return success_count
        
    except FileNotFoundError:
        print(f"❌ 文件不存在: {file_path}")
        return 0
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return 0


def import_devices_from_file(file_path='设备.txt', client_id=None):
    """
    从文件导入设备到数据库
    
    Args:
        file_path: 设备文件路径
        client_id: 分配给哪个客户端（None=不分配）
    """
    print(f"\n{'='*60}")
    print(f"📥 正在导入设备: {file_path}")
    print(f"{'='*60}")
    
    try:
        # 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"✅ 读取到 {len(lines)} 行数据")
        
        # 预解析参数
        params = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) < 5:
                print(f"  ⚠️ 格式错误，跳过一行")
                continue
            devid, miniwua, sgext, umt, utdid = parts[0], parts[1], parts[2], parts[3], parts[4]
            params.append((client_id, devid, miniwua, sgext, umt, utdid))

        # 单线程批量导入（临时表 + 去重）
        success_count, skip_count = _sequential_bulk_insert_devices(params, client_id, batch_size=100, label="设备 进度")
        
        print(f"\n✅ 导入完成:")
        print(f"  - 成功: {success_count} 个")
        print(f"  - 跳过(重复): {skip_count} 个")
        
        return success_count
        
    except FileNotFoundError:
        print(f"❌ 文件不存在: {file_path}")
        return 0
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return 0


def show_stats():
    """显示数据库统计信息"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        print(f"\n{'='*60}")
        print("📊 数据库统计")
        print(f"{'='*60}")
        
        # Cookie统计
        cursor.execute("SELECT COUNT(*) as total FROM tb_cookies")
        cookie_total = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM tb_cookies WHERE client_id IS NULL")
        cookie_unassigned = cursor.fetchone()['total']
        
        print(f"🍪 Cookie总数: {cookie_total}")
        print(f"   - 未分配: {cookie_unassigned}")
        print(f"   - 已分配: {cookie_total - cookie_unassigned}")
        
        # 设备统计
        cursor.execute("SELECT COUNT(*) as total FROM tb_devices")
        device_total = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM tb_devices WHERE client_id IS NULL")
        device_unassigned = cursor.fetchone()['total']
        
        print(f"📱 设备总数: {device_total}")
        print(f"   - 未分配: {device_unassigned}")
        print(f"   - 已分配: {device_total - device_unassigned}")
        
        # 客户端分配统计
        cursor.execute("""
            SELECT c.client_name, c.client_key,
                   COUNT(DISTINCT ck.id) as cookie_count,
                   COUNT(DISTINCT d.id) as device_count
            FROM tb_clients c
            LEFT JOIN tb_cookies ck ON c.id = ck.client_id
            LEFT JOIN tb_devices d ON c.id = d.client_id
            WHERE c.is_active = 1
            GROUP BY c.id
            ORDER BY c.id
        """)
        
        clients = cursor.fetchall()
        
        print(f"\n📊 客户端数据分配:")
        print(f"{'客户端名称':<15} {'密钥':<20} {'Cookie':<10} {'设备':<10}")
        print("-" * 60)
        
        for client in clients:
            name = client['client_name'] or '未命名'
            key = client['client_key']
            cookie_count = client['cookie_count']
            device_count = client['device_count']
            
            print(f"{name:<15} {key:<20} {cookie_count:<10} {device_count:<10}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ 获取统计信息失败: {e}")


def assign_data_to_client(client_id, cookie_count=0, device_count=0):
    """
    分配数据给指定客户端
    
    Args:
        client_id: 客户端ID
        cookie_count: 分配的Cookie数量
        device_count: 分配的设备数量
    """
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print(f"\n{'='*60}")
        print(f"🔧 正在分配数据给客户端 {client_id}")
        print(f"{'='*60}")
        
        # 分配Cookie
        if cookie_count > 0:
            sql = """
                UPDATE tb_cookies 
                SET client_id = %s 
                WHERE client_id IS NULL 
                LIMIT %s
            """
            cursor.execute(sql, (client_id, cookie_count))
            affected = cursor.rowcount
            print(f"✅ 分配Cookie: {affected} 个")
        
        # 分配设备
        if device_count > 0:
            sql = """
                UPDATE tb_devices 
                SET client_id = %s 
                WHERE client_id IS NULL 
                LIMIT %s
            """
            cursor.execute(sql, (client_id, device_count))
            affected = cursor.rowcount
            print(f"✅ 分配设备: {affected} 个")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ 分配完成")
        
    except Exception as e:
        print(f"❌ 分配失败: {e}")


def main():
    """主函数"""
    print("="*60)
    print("  淘宝直播刷量系统 - 数据导入工具")
    print("="*60)
    print()
    print("请选择操作:")
    print("1. 导入Cookie (账号.txt)")
    print("2. 导入设备 (设备.txt)")
    print("3. 导入全部 (账号.txt + 设备.txt)")
    print("4. 查看数据统计")
    print("5. 分配数据给客户端")
    print("0. 退出")
    print()
    
    choice = input("请输入选项 (0-5): ").strip()
    
    if choice == '1':
        file_path = input("Cookie文件路径 (默认:账号.txt): ").strip() or '账号.txt'
        client_id_input = input("分配给客户端ID (留空=不分配): ").strip()
        client_id = int(client_id_input) if client_id_input else None
        import_cookies_from_file(file_path, client_id)
        show_stats()
        
    elif choice == '2':
        file_path = input("设备文件路径 (默认:设备.txt): ").strip() or '设备.txt'
        client_id_input = input("分配给客户端ID (留空=不分配): ").strip()
        client_id = int(client_id_input) if client_id_input else None
        import_devices_from_file(file_path, client_id)
        show_stats()
        
    elif choice == '3':
        cookie_file = input("Cookie文件路径 (默认:账号.txt): ").strip() or '账号.txt'
        device_file = input("设备文件路径 (默认:设备.txt): ").strip() or '设备.txt'
        client_id_input = input("分配给客户端ID (留空=不分配): ").strip()
        client_id = int(client_id_input) if client_id_input else None
        
        import_cookies_from_file(cookie_file, client_id)
        import_devices_from_file(device_file, client_id)
        show_stats()
        
    elif choice == '4':
        show_stats()
        
    elif choice == '5':
        show_stats()
        print()
        client_id = int(input("客户端ID: ").strip())
        cookie_count = int(input("分配Cookie数量: ").strip())
        device_count = int(input("分配设备数量: ").strip())
        assign_data_to_client(client_id, cookie_count, device_count)
        show_stats()
        
    elif choice == '0':
        print("👋 再见！")
        sys.exit(0)
        
    else:
        print("❌ 无效的选项")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，退出程序")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()


