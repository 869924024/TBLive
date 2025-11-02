"""
淘宝直播刷量系统 - API服务端
提供Cookie和设备参数的远程获取接口（带鉴权）
"""

from flask import Flask, request, jsonify
import pymysql
from datetime import datetime
import json

app = Flask(__name__)


def get_client_identifier(client_key, request_obj):
    """
    生成客户端唯一标识：client_key@IP
    
    例如：client_key_001@192.168.1.100
    这样即使多台机器用同一个key也能区分
    """
    # 获取客户端真实IP
    if request_obj.headers.get('X-Forwarded-For'):
        client_ip = request_obj.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request_obj.headers.get('X-Real-IP'):
        client_ip = request_obj.headers.get('X-Real-IP')
    else:
        client_ip = request_obj.remote_addr
    
    return f"{client_key}@{client_ip}"

# ============================================
# 数据库配置（根据实际情况修改）
# ============================================
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'tb_live',
    'password': 'hjj2819597',  # 修改为你的数据库密码
    'database': 'tb_live',         # 修改为你的数据库名
    'charset': 'utf8mb4',
    'connect_timeout': 10,
    'read_timeout': 30,
    'write_timeout': 30
}


def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)


def verify_client_key(client_key):
    """
    验证客户端密钥
    
    返回: (是否有效, 客户端ID, 客户端名称)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        sql = "SELECT id, client_name, is_active FROM tb_clients WHERE client_key = %s"
        cursor.execute(sql, (client_key,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result and result['is_active'] == 1:
            return True, result['id'], result['client_name']
        else:
            return False, None, None
            
    except Exception as e:
        print(f"数据库错误: {e}")
        return False, None, None


@app.route('/api/ping', methods=['GET'])
def ping():
    """健康检查接口"""
    return jsonify({
        'success': True,
        'message': 'API服务运行正常',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/fetch_cookies', methods=['POST'])
def fetch_cookies():
    """
    获取Cookie列表（需要鉴权）
    
    请求参数:
        - client_key: 客户端密钥
        - limit: 获取数量（默认50）
    
    返回:
        - success: 是否成功
        - data: Cookie列表
        - count: 数量
    """
    try:
        # 获取请求参数
        data = request.get_json()
        client_key = data.get('client_key')
        limit = data.get('limit', 50)
        
        if not client_key:
            return jsonify({
                'success': False,
                'message': '缺少client_key参数'
            }), 400
        
        # 验证客户端密钥
        is_valid, client_id, client_name = verify_client_key(client_key)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': '无效的client_key或客户端已禁用'
            }), 401
        
        # 查询该客户端分配的Cookie
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        sql = """
            SELECT id, cookie, uid, status, created_at, last_used_at 
            FROM tb_cookies 
            WHERE client_id = %s AND status = 1 
            ORDER BY COALESCE(last_used_at, '1970-01-01') ASC
            LIMIT %s
        """
        cursor.execute(sql, (client_id, limit))
        results = cursor.fetchall()
        
        # 更新最后拉取时间
        update_sql = "UPDATE tb_clients SET last_fetch_at = %s WHERE id = %s"
        cursor.execute(update_sql, (datetime.now(), client_id))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        # 格式化返回数据
        cookies = []
        for row in results:
            cookies.append({
                'id': row['id'],
                'cookie': row['cookie'],
                'uid': row['uid'],
                'status': row['status']
            })
        
        return jsonify({
            'success': True,
            'message': f'成功获取{len(cookies)}个Cookie',
            'client_name': client_name,
            'data': cookies,
            'count': len(cookies)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }), 500


@app.route('/api/fetch_devices', methods=['POST'])
def fetch_devices():
    """
    获取设备参数列表（需要鉴权）
    
    请求参数:
        - client_key: 客户端密钥
        - limit: 获取数量（默认50）
    
    返回:
        - success: 是否成功
        - data: 设备列表
        - count: 数量
    """
    try:
        # 获取请求参数
        data = request.get_json()
        client_key = data.get('client_key')
        limit = data.get('limit', 50)
        
        if not client_key:
            return jsonify({
                'success': False,
                'message': '缺少client_key参数'
            }), 400
        
        # 验证客户端密钥
        is_valid, client_id, client_name = verify_client_key(client_key)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': '无效的client_key或客户端已禁用'
            }), 401
        
        # 查询该客户端分配的设备
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        sql = """
            SELECT id, devid, miniwua, sgext, umt, utdid, status, created_at, last_used_at 
            FROM tb_devices 
            WHERE client_id = %s AND status = 1 
            ORDER BY COALESCE(last_used_at, '1970-01-01') ASC
            LIMIT %s
        """
        cursor.execute(sql, (client_id, limit))
        results = cursor.fetchall()
        
        # 更新最后拉取时间
        update_sql = "UPDATE tb_clients SET last_fetch_at = %s WHERE id = %s"
        cursor.execute(update_sql, (datetime.now(), client_id))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        # 格式化返回数据（按照设备.txt格式）
        devices = []
        for row in results:
            device_str = f"{row['devid']}\t{row['miniwua']}\t{row['sgext']}\t{row['umt']}\t{row['utdid']}"
            devices.append({
                'id': row['id'],
                'device_string': device_str,
                'devid': row['devid'],
                'miniwua': row['miniwua'],
                'sgext': row['sgext'],
                'umt': row['umt'],
                'utdid': row['utdid'],
                'status': row['status']
            })
        
        return jsonify({
            'success': True,
            'message': f'成功获取{len(devices)}个设备参数',
            'client_name': client_name,
            'data': devices,
            'count': len(devices)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }), 500


@app.route('/api/update_cookie_status', methods=['POST'])
def update_cookie_status():
    """
    更新Cookie状态（标记失效/封禁）
    
    请求参数:
        - client_key: 客户端密钥
        - cookie_id: Cookie ID
        - status: 状态（0=失效，1=正常，2=封禁）
    """
    try:
        data = request.get_json()
        client_key = data.get('client_key')
        cookie_id = data.get('cookie_id')
        status = data.get('status')
        
        if not all([client_key, cookie_id is not None, status is not None]):
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            }), 400
        
        # 验证客户端密钥
        is_valid, client_id, _ = verify_client_key(client_key)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': '无效的client_key'
            }), 401
        
        # 更新状态
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = "UPDATE tb_cookies SET status = %s WHERE id = %s AND client_id = %s"
        cursor.execute(sql, (status, cookie_id, client_id))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '状态更新成功'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }), 500


@app.route('/api/update_device_status', methods=['POST'])
def update_device_status():
    """
    更新设备状态（标记失效/封禁）
    
    请求参数:
        - client_key: 客户端密钥
        - device_id: 设备ID
        - status: 状态（0=失效，1=正常，2=封禁）
    """
    try:
        data = request.get_json()
        client_key = data.get('client_key')
        device_id = data.get('device_id')
        status = data.get('status')
        
        if not all([client_key, device_id is not None, status is not None]):
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            }), 400
        
        # 验证客户端密钥
        is_valid, client_id, _ = verify_client_key(client_key)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': '无效的client_key'
            }), 401
        
        # 更新状态
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = "UPDATE tb_devices SET status = %s WHERE id = %s AND client_id = %s"
        cursor.execute(sql, (status, device_id, client_id))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '状态更新成功'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }), 500


@app.route('/api/allocate_resources', methods=['POST'])
def allocate_resources():
    """
    获取可用资源（不锁定）- 任务开始前调用
    
    改进逻辑：
    1. 只查询可用资源，不锁定
    2. 支持分页拉取（offset参数）
    3. 预热时客户端自行筛选，预热后调用lock接口锁定
    
    请求参数:
        - client_key: 客户端密钥
        - cookie_count: Cookie数量（0=全部，-1=不拉取，>0=指定数量）
        - device_count: 设备数量（0=全部，-1=不拉取，>0=指定数量）
        - cookie_offset: Cookie偏移量（默认0，用于分页）
        - device_offset: 设备偏移量（默认0，用于分页）
        - include_cooldown: 是否包含冷却期的资源（默认False，用于刷新显示）
    
    返回:
        - cookies: Cookie列表（未锁定）
        - devices: 设备列表（未锁定）
    """
    try:
        data = request.get_json()
        client_key = data.get('client_key')
        cookie_count = data.get('cookie_count', 0)  # 0=全部，-1=不拉
        device_count = data.get('device_count', 0)  # 0=全部，-1=不拉
        cookie_offset = data.get('cookie_offset', 0)  # 分页偏移
        device_offset = data.get('device_offset', 0)  # 分页偏移
        include_cooldown = data.get('include_cooldown', False)  # 是否包含冷却期的资源（用于刷新显示）
        
        if not client_key:
            return jsonify({
                'success': False,
                'message': '缺少client_key参数'
            }), 400
        
        # 验证客户端
        is_valid, client_id, client_name = verify_client_key(client_key)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': '无效的client_key或客户端已禁用'
            }), 401
        
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # ===== 1. 查询可用Cookie（不锁定）=====
        cookies = []
        if cookie_count != -1:  # -1表示不拉取
            # 构建查询条件：is_locked=0 是必须的，cooldown_until 根据 include_cooldown 决定
            if include_cooldown:
                # 包含冷却期的：只过滤 is_locked=0 和 status=1
                cooldown_filter = ""
                cookie_params = [client_id]
            else:
                # 不包含冷却期的：还要过滤 cooldown_until
                cooldown_filter = "AND (cooldown_until IS NULL OR cooldown_until < NOW())"
                cookie_params = [client_id]
            
            if cookie_count > 0:
                # 拉取指定数量（支持分页）
                sql = f"""
                    SELECT id, cookie, uid 
                    FROM tb_cookies 
                    WHERE client_id = %s 
                      AND status = 1 
                      AND is_locked = 0
                      {cooldown_filter}
                    ORDER BY COALESCE(last_used_at, '1970-01-01') ASC
                    LIMIT %s OFFSET %s
                """
                cookie_params.extend([cookie_count, cookie_offset])
                cursor.execute(sql, cookie_params)
            else:
                # cookie_count=0，拉取全部
                sql = f"""
                    SELECT id, cookie, uid 
                    FROM tb_cookies 
                    WHERE client_id = %s 
                      AND status = 1 
                      AND is_locked = 0
                      {cooldown_filter}
                    ORDER BY COALESCE(last_used_at, '1970-01-01') ASC
                """
                cursor.execute(sql, cookie_params)
            
            cookies = cursor.fetchall()
        
        # ===== 2. 查询可用设备（不锁定）=====
        devices = []
        if device_count != -1:  # -1表示不拉取
            if device_count > 0:
                # 拉取指定数量（支持分页）
                cursor.execute("""
                    SELECT id, devid, miniwua, sgext, umt, utdid 
                    FROM tb_devices 
                    WHERE client_id = %s 
                      AND status = 1 
                      AND is_locked = 0
                      AND (cooldown_until IS NULL OR cooldown_until < NOW())
                    ORDER BY COALESCE(last_used_at, '1970-01-01') ASC
                    LIMIT %s OFFSET %s
                """, (client_id, device_count, device_offset))
            else:
                # device_count=0，拉取全部
                cursor.execute("""
                    SELECT id, devid, miniwua, sgext, umt, utdid 
                    FROM tb_devices 
                    WHERE client_id = %s 
                      AND status = 1 
                      AND is_locked = 0
                      AND (cooldown_until IS NULL OR cooldown_until < NOW())
                    ORDER BY COALESCE(last_used_at, '1970-01-01') ASC
                """, (client_id,))
            
            devices = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # 格式化返回数据
        cookie_list = [{
            'id': c['id'],
            'cookie': c['cookie'],
            'uid': c['uid']
        } for c in cookies]
        
        device_list = [{
            'id': d['id'],
            'device_string': f"{d['devid']}\t{d['miniwua']}\t{d['sgext']}\t{d['umt']}\t{d['utdid']}",
            'devid': d['devid']
        } for d in devices]
        
        return jsonify({
            'success': True,
            'message': f'查询到 {len(cookie_list)} 个Cookie，{len(device_list)} 个设备（未锁定）',
            'client_name': client_name,
            'data': {
                'cookies': cookie_list,
                'devices': device_list
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }), 500


@app.route('/api/lock_resources', methods=['POST'])
def lock_resources():
    """
    锁定指定资源 - 预热完成后调用
    
    用途：
    1. 预热时筛选出实际使用的 Cookie 和设备
    2. 锁定这些资源，防止其他客户端使用
    
    请求参数:
        - client_key: 客户端密钥
        - cookie_ids: 要锁定的 Cookie ID 列表（可选）
        - device_ids: 要锁定的设备ID列表（可选）
    """
    try:
        data = request.get_json()
        client_key = data.get('client_key')
        cookie_ids = data.get('cookie_ids', [])
        device_ids = data.get('device_ids', [])
        
        if not client_key:
            return jsonify({
                'success': False,
                'message': '缺少client_key参数'
            }), 400
        
        if not cookie_ids and not device_ids:
            return jsonify({
                'success': True,
                'message': '没有需要锁定的资源',
                'data': {
                    'locked_cookies': 0,
                    'locked_devices': 0
                }
            })
        
        # 验证客户端
        is_valid, client_id, _ = verify_client_key(client_key)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': '无效的client_key'
            }), 401
        
        # 生成客户端标识（client_key@IP）
        client_identifier = get_client_identifier(client_key, request)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ===== 1. 锁定Cookie =====
        locked_cookies = 0
        if cookie_ids:
            placeholders = ','.join(['%s'] * len(cookie_ids))
            cursor.execute(f"""
                UPDATE tb_cookies 
                SET is_locked = 1,
                    locked_by_client = %s,
                    locked_at = NOW()
                WHERE id IN ({placeholders})
                  AND is_locked = 0
                  AND client_id = %s
            """, [client_identifier] + cookie_ids + [client_id])
            locked_cookies = cursor.rowcount
        
        # ===== 2. 锁定设备 =====
        locked_devices = 0
        if device_ids:
            placeholders = ','.join(['%s'] * len(device_ids))
            cursor.execute(f"""
                UPDATE tb_devices 
                SET is_locked = 1,
                    locked_by_client = %s,
                    locked_at = NOW()
                WHERE id IN ({placeholders})
                  AND is_locked = 0
                  AND client_id = %s
            """, [client_identifier] + device_ids + [client_id])
            locked_devices = cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'成功锁定 {locked_cookies} 个Cookie，{locked_devices} 个设备',
            'data': {
                'locked_cookies': locked_cookies,
                'locked_devices': locked_devices
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }), 500


@app.route('/api/release_resources', methods=['POST'])
def release_resources():
    """
    释放资源并标记冷却 - 任务结束后调用
    
    特点：
    1. 解除锁定
    2. 标记进入12小时冷却期
    3. 防止其他客户端重复使用
    
    请求参数:
        - client_key: 客户端密钥
        - cookie_ids: Cookie ID列表
        - device_ids: 设备ID列表
        - cooldown_hours: 冷却时长（小时，默认12）
    """
    try:
        data = request.get_json()
        client_key = data.get('client_key')
        cookie_ids = data.get('cookie_ids', [])
        device_ids = data.get('device_ids', [])
        cooldown_hours = data.get('cooldown_hours', 12)
        
        if not client_key:
            return jsonify({
                'success': False,
                'message': '缺少client_key参数'
            }), 400
        
        # 验证客户端
        is_valid, client_id, _ = verify_client_key(client_key)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': '无效的client_key'
            }), 401
        
        # 生成客户端标识（client_key@IP）
        client_identifier = get_client_identifier(client_key, request)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ===== 1. 释放Cookie =====
        if cookie_ids:
            placeholders = ','.join(['%s'] * len(cookie_ids))
            # 不清空 locked_by_client 和 locked_at，保留历史记录用于追踪
            # 判断是否正在被锁定的逻辑：is_locked = 1 且 locked_by_client != 当前客户端
            cursor.execute(f"""
                UPDATE tb_cookies 
                SET is_locked = 0,
                    cooldown_until = DATE_ADD(NOW(), INTERVAL %s HOUR),
                    last_used_at = NOW()
                WHERE id IN ({placeholders})
                  AND locked_by_client = %s
                  AND is_locked = 1
            """, [cooldown_hours] + cookie_ids + [client_identifier])
            
            released_cookies = cursor.rowcount
        else:
            released_cookies = 0
        
        # ===== 2. 释放设备 =====
        if device_ids:
            placeholders = ','.join(['%s'] * len(device_ids))
            # 不清空 locked_by_client 和 locked_at，保留历史记录用于追踪
            # 判断是否正在被锁定的逻辑：is_locked = 1 且 locked_by_client != 当前客户端
            cursor.execute(f"""
                UPDATE tb_devices 
                SET is_locked = 0,
                    cooldown_until = DATE_ADD(NOW(), INTERVAL %s HOUR),
                    last_used_at = NOW()
                WHERE id IN ({placeholders})
                  AND locked_by_client = %s
                  AND is_locked = 1
            """, [cooldown_hours] + device_ids + [client_identifier])
            
            released_devices = cursor.rowcount
        else:
            released_devices = 0
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'成功释放 {released_cookies} 个Cookie，{released_devices} 个设备，冷却{cooldown_hours}小时',
            'data': {
                'released_cookies': released_cookies,
                'released_devices': released_devices
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }), 500


@app.route('/api/log_task', methods=['POST'])
def log_task():
    """
    记录任务日志 - 任务完成后调用
    
    请求参数:
        - client_key: 客户端密钥
        - live_id: 直播间ID
        - view_count_before: 操作前观看数
        - view_count_after: 操作后观看数
        - success_count: 成功数
        - fail_count: 失败数
        - started_at: 开始时间（可选）
    """
    try:
        data = request.get_json()
        client_key = data.get('client_key')
        live_id = data.get('live_id')
        view_count_before = data.get('view_count_before', 0)
        view_count_after = data.get('view_count_after', 0)
        success_count = data.get('success_count', 0)
        fail_count = data.get('fail_count', 0)
        started_at = data.get('started_at')  # 可选
        
        if not client_key:
            return jsonify({
                'success': False,
                'message': '缺少client_key参数'
            }), 400
        
        # 验证客户端
        is_valid, client_id, _ = verify_client_key(client_key)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': '无效的client_key'
            }), 401
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 计算增量
        increment = view_count_after - view_count_before
        
        # 插入任务日志
        if started_at:
            cursor.execute("""
                INSERT INTO tb_task_logs 
                (client_id, live_id, view_count_before, view_count_after, 
                 increment, success_count, fail_count, started_at, finished_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (client_id, live_id, view_count_before, view_count_after,
                  increment, success_count, fail_count, started_at))
        else:
            cursor.execute("""
                INSERT INTO tb_task_logs 
                (client_id, live_id, view_count_before, view_count_after, 
                 increment, success_count, fail_count, finished_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """, (client_id, live_id, view_count_before, view_count_after,
                  increment, success_count, fail_count))
        
        conn.commit()
        task_log_id = cursor.lastrowid
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'任务日志记录成功（ID: {task_log_id}）',
            'data': {
                'task_log_id': task_log_id,
                'increment': increment
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 淘宝直播刷量系统 - API服务")
    print("=" * 60)
    print("📡 监听地址: 0.0.0.0:5000")
    print("🔐 需要client_key进行鉴权")
    print("=" * 60)
    print()
    
    # 启动Flask服务
    app.run(
        host='0.0.0.0',  # 监听所有网卡
        port=5000,        # 端口
        debug=False,      # 生产环境关闭debug
        threaded=True     # 多线程支持
    )

