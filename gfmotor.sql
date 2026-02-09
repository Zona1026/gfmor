SET FOREIGN_KEY_CHECKS = 0;
SET @OLD_FOREIGN_KEY_CHECKS = @@FOREIGN_KEY_CHECKS;

CREATE DATABASE IF NOT EXISTS `gfmotor`;
USE `gfmotor`;
--
-- Table structure for table `admins`
--

DROP TABLE IF EXISTS `admins`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `admins` (
  `帳號` int NOT NULL,
  `密碼` varchar(45) NOT NULL,
  `名稱` varchar(45) NOT NULL,
  `權限` enum('最高級','管理層','一般') DEFAULT '一般',
  PRIMARY KEY (`帳號`),
  UNIQUE KEY `帳號_UNIQUE` (`帳號`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `bookings`
--

DROP TABLE IF EXISTS `bookings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bookings` (
  `預約單號` int unsigned NOT NULL AUTO_INCREMENT,
  `Google ID` varchar(255) NOT NULL,
  `車籍ID` int NOT NULL,
  `預約時間` datetime NOT NULL,
  `類別` enum('維修','保養','諮詢') NOT NULL,
  `預約單成立時間` datetime DEFAULT CURRENT_TIMESTAMP,
  `狀態` enum('預約中','預約取消','已超時','已結案','後台開放時間') NOT NULL,
  `備註` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`預約單號`),
  KEY `關聯_idx` (`Google ID`),
  KEY `車籍關聯` (`車籍ID`),
  CONSTRAINT `車籍關聯` FOREIGN KEY (`車籍ID`) REFERENCES `motor` (`ID`),
  CONSTRAINT `關聯` FOREIGN KEY (`Google ID`) REFERENCES `users` (`Google ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `consumptions`
--

DROP TABLE IF EXISTS `consumptions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `consumptions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `Google ID` varchar(255) NOT NULL,
  `消費金額` int NOT NULL,
  `消費項目` varchar(100) NOT NULL,
  `消費時間` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `Google ID` (`Google ID`),
  CONSTRAINT `consumptions_ibfk_1` FOREIGN KEY (`Google ID`) REFERENCES `users` (`Google ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `motor`
--

DROP TABLE IF EXISTS `motor`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `motor` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `Google ID` varchar(255) NOT NULL,
  `車牌` varchar(45) NOT NULL,
  `引擎號碼` varchar(45) DEFAULT NULL,
  `車種` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`ID`),
  KEY `關聯_idx` (`Google ID`),
  KEY `fk_motor_users_idx` (`Google ID`),
  CONSTRAINT `fk_motor_users` FOREIGN KEY (`Google ID`) REFERENCES `users` (`Google ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `portfolio_items`
--

DROP TABLE IF EXISTS `portfolio_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `portfolio_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `標題` varchar(100) NOT NULL,
  `描述` varchar(500) DEFAULT NULL,
  `分類` varchar(50) NOT NULL,
  `圖片路徑` varchar(255) NOT NULL,
  `上傳時間` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `Google ID` varchar(255) NOT NULL,
  `車主姓名` varchar(10) NOT NULL,
  `電話` varchar(10) DEFAULT NULL,
  `email` varchar(100) NOT NULL,
  `類別` enum('MEMBER','ADMIN') DEFAULT 'MEMBER',
  `加入時間` datetime DEFAULT CURRENT_TIMESTAMP,
  `會員等級` varchar(45) DEFAULT NULL,
  `累積消費` int DEFAULT NULL,
  `車牌` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`Google ID`),
  UNIQUE KEY `email_UNIQUE` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


--
-- Table structure for table `products`
--
DROP TABLE IF EXISTS `products`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `products` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL COMMENT '品名',
  `description` text COMMENT '描述',
  `price` int(10) unsigned NOT NULL COMMENT '價格',
  `stock` int(10) unsigned NOT NULL DEFAULT '0' COMMENT '庫存數量',
  `category` varchar(50) DEFAULT NULL COMMENT '分類',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='庫存商品';
/*!40101 SET character_set_client = @saved_cs_client */;

/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `work_orders`
--
DROP TABLE IF EXISTS `work_orders`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `work_orders` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `booking_id` int(10) unsigned NOT NULL COMMENT '對應的預約單號',
  `status` enum('待處理','處理中','待付款','已完成','取消') NOT NULL DEFAULT '待處理',
  `total_amount` int(10) unsigned NOT NULL DEFAULT '0' COMMENT '總金額',
  `notes` text COMMENT '工單備註',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `completed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_work_orders_bookings_idx` (`booking_id`),
  CONSTRAINT `fk_work_orders_bookings` FOREIGN KEY (`booking_id`) REFERENCES `bookings` (`預約單號`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工單';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `work_order_items`
--
DROP TABLE IF EXISTS `work_order_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `work_order_items` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `work_order_id` int(10) unsigned NOT NULL COMMENT '對應的工單ID',
  `product_id` int(10) unsigned NOT NULL COMMENT '對應的商品ID',
  `quantity` int(10) unsigned NOT NULL COMMENT '數量',
  `unit_price` int(10) unsigned NOT NULL COMMENT '當時的單價',
  PRIMARY KEY (`id`),
  KEY `fk_work_order_items_work_orders_idx` (`work_order_id`),
  KEY `fk_work_order_items_products_idx` (`product_id`),
  CONSTRAINT `fk_work_order_items_products` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`),
  CONSTRAINT `fk_work_order_items_work_orders` FOREIGN KEY (`work_order_id`) REFERENCES `work_orders` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工單項目詳情';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `orders`
--
DROP TABLE IF EXISTS `orders`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `orders` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `google_id` varchar(255) NOT NULL COMMENT '對應的user Google ID',
  `status` enum('待處理','處理中','已出貨','已完成','已取消') NOT NULL DEFAULT '待處理' COMMENT '訂單狀態',
  `total_amount` int(10) unsigned NOT NULL COMMENT '訂單總金額',
  `recipient_name` varchar(50) NOT NULL COMMENT '收件人姓名',
  `recipient_phone` varchar(20) NOT NULL COMMENT '收件人電話',
  `shipping_address` varchar(255) NOT NULL COMMENT '運送地址',
  `notes` text COMMENT '訂單備註',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_orders_users_idx` (`google_id`),
  CONSTRAINT `fk_orders_users` FOREIGN KEY (`google_id`) REFERENCES `users` (`Google ID`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='客戶線上訂單';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `order_items`
--
DROP TABLE IF EXISTS `order_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `order_items` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `order_id` int(10) unsigned NOT NULL COMMENT '對應的訂單ID',
  `product_id` int(10) unsigned NOT NULL COMMENT '對應的商品ID',
  `quantity` int(10) unsigned NOT NULL COMMENT '數量',
  `unit_price` int(10) unsigned NOT NULL COMMENT '購買時的單價',
  PRIMARY KEY (`id`),
  KEY `fk_order_items_orders_idx` (`order_id`),
  KEY `fk_order_items_products_idx` (`product_id`),
  CONSTRAINT `fk_order_items_orders` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_order_items_products_2` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='訂單內的商品項目';
/*!40101 SET character_set_client = @saved_cs_client */;

SET FOREIGN_KEY_CHECKS = @OLD_FOREIGN_KEY_CHECKS;