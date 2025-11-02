"""
淘宝直播刷量系统 - API服务端
提供Cookie和设备参数的远程获取接口（带鉴权）
"""

from flask import Flask, request, jsonify
import pymysql
from datetime import datetime
import json

app = Flask(__name__)

# ============================================
# 数据库配置（根据实际情况修改）
# ============================================
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'tb_live',
    'password': 'hjj2819597',  # 修改为你的数据库密码
    'database': 'tb_live',         # 修改为你的数据库名
    'charset': 'utf8mb4'
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

