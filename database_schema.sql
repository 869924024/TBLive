-- ============================================
-- 淘宝直播刷量系统 - 数据库表结构
-- ============================================

-- 1. 客户端配置表（用于鉴权和分配数据）
CREATE TABLE IF NOT EXISTS `tb_clients` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '客户端ID',
  `client_key` VARCHAR(64) UNIQUE NOT NULL COMMENT '客户端唯一标识（用于鉴权）',
  `client_name` VARCHAR(100) DEFAULT NULL COMMENT '客户端名称（如：电脑1、电脑2）',
  `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否激活（0=禁用，1=启用）',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `last_fetch_at` TIMESTAMP NULL DEFAULT NULL COMMENT '最后拉取时间',
  INDEX `idx_client_key` (`client_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户端配置表';

-- 2. Cookie账号表
CREATE TABLE IF NOT EXISTS `tb_cookies` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Cookie ID',
  `client_id` INT DEFAULT NULL COMMENT '分配给哪个客户端（NULL=未分配）',
  `cookie` TEXT NOT NULL COMMENT 'Cookie完整内容',
  `uid` VARCHAR(50) DEFAULT NULL COMMENT '淘宝UID',
  `status` TINYINT(1) DEFAULT 1 COMMENT '状态（0=失效，1=正常，2=封禁）',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `last_used_at` TIMESTAMP NULL DEFAULT NULL COMMENT '最后使用时间',
  INDEX `idx_client_id` (`client_id`),
  INDEX `idx_status` (`status`),
  FOREIGN KEY (`client_id`) REFERENCES `tb_clients`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Cookie账号表';

-- 3. 设备参数表
CREATE TABLE IF NOT EXISTS `tb_devices` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '设备ID',
  `client_id` INT DEFAULT NULL COMMENT '分配给哪个客户端（NULL=未分配）',
  `devid` VARCHAR(255) NOT NULL COMMENT '设备ID',
  `miniwua` TEXT NOT NULL COMMENT 'mini-wua',
  `sgext` TEXT NOT NULL COMMENT 'sgext',
  `umt` TEXT NOT NULL COMMENT 'umt',
  `utdid` VARCHAR(255) NOT NULL COMMENT 'utdid',
  `status` TINYINT(1) DEFAULT 1 COMMENT '状态（0=失效，1=正常，2=封禁）',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `last_used_at` TIMESTAMP NULL DEFAULT NULL COMMENT '最后使用时间',
  INDEX `idx_client_id` (`client_id`),
  INDEX `idx_status` (`status`),
  INDEX `idx_devid` (`devid`(100)),
  FOREIGN KEY (`client_id`) REFERENCES `tb_clients`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备参数表';

-- 4. 任务记录表（可选，用于统计）
CREATE TABLE IF NOT EXISTS `tb_task_logs` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '任务ID',
  `client_id` INT NOT NULL COMMENT '客户端ID',
  `live_id` VARCHAR(100) DEFAULT NULL COMMENT '直播间ID',
  `share_code` VARCHAR(255) DEFAULT NULL COMMENT '淘口令',
  `view_count_before` INT DEFAULT 0 COMMENT '操作前观看数',
  `view_count_after` INT DEFAULT 0 COMMENT '操作后观看数',
  `increment` INT DEFAULT 0 COMMENT '增量',
  `success_count` INT DEFAULT 0 COMMENT '成功数',
  `fail_count` INT DEFAULT 0 COMMENT '失败数',
  `started_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间',
  `finished_at` TIMESTAMP NULL DEFAULT NULL COMMENT '结束时间',
  INDEX `idx_client_id` (`client_id`),
  INDEX `idx_live_id` (`live_id`),
  FOREIGN KEY (`client_id`) REFERENCES `tb_clients`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务记录表';

-- ============================================
-- 初始化示例数据（10个客户端）
-- ============================================

INSERT INTO `tb_clients` (`client_key`, `client_name`, `is_active`) VALUES
('client_key_001', '电脑1', 1),
('client_key_002', '电脑2', 1),
('client_key_003', '电脑3', 1),
('client_key_004', '电脑4', 1),
('client_key_005', '电脑5', 1),
('client_key_006', '电脑6', 1),
('client_key_007', '电脑7', 1),
('client_key_008', '电脑8', 1),
('client_key_009', '电脑9', 1),
('client_key_010', '电脑10', 1);

-- ============================================
-- 使用说明
-- ============================================
-- 1. 每台电脑使用不同的 client_key 进行鉴权
-- 2. Cookie和设备分配给对应的 client_id
-- 3. 查询示例：
--    SELECT * FROM tb_cookies WHERE client_id = 1 AND status = 1;
--    SELECT * FROM tb_devices WHERE client_id = 1 AND status = 1;

