-- MySQL dump 10.13  Distrib 8.0.44, for Win64 (x86_64)
--
-- Host: gfmotor-gfmotor001.j.aivencloud.com    Database: gfmotor
-- ------------------------------------------------------
-- Server version	8.0.35

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
SET @MYSQLDUMP_TEMP_LOG_BIN = @@SESSION.SQL_LOG_BIN;
SET @@SESSION.SQL_LOG_BIN= 0;

--
-- GTID state at the beginning of the backup 
--

SET @@GLOBAL.GTID_PURGED=/*!80000 '+'*/ '0529510d-d82e-11f0-870a-1609d6c8b91b:1-35,
0e6fb957-d590-11f0-9983-22ec812373a9:1-75,
e96a4138-d6a7-11f0-9efc-72b246dfb798:1-15';

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
  `車種` varchar(45) NOT NULL,
  `預約時間` datetime NOT NULL,
  `類別` enum('維修','保養','諮詢') NOT NULL,
  `預約單成立時間` datetime DEFAULT CURRENT_TIMESTAMP,
  `狀態` enum('預約中','預約取消','已超時','已結案','後台開放時間') NOT NULL,
  `引擎號碼` varchar(15) DEFAULT NULL,
  `備註` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`預約單號`),
  KEY `關聯_idx` (`Google ID`),
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
-- Table structure for table `portfolio_items`
--

DROP TABLE IF EXISTS `portfolio_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `portfolio_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `標題` varchar(100) NOT NULL,
  `分類` varchar(50) NOT NULL,
  `圖片路徑` varchar(255) NOT NULL,
  `上傳時間` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `slot_configurations`
--

DROP TABLE IF EXISTS `slot_configurations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `slot_configurations` (
  `id` int NOT NULL AUTO_INCREMENT,
  `指定時間` datetime NOT NULL,
  `最大人數` int DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_slot_configurations_指定時間` (`指定時間`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
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
  PRIMARY KEY (`Google ID`),
  UNIQUE KEY `email_UNIQUE` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
SET @@SESSION.SQL_LOG_BIN = @MYSQLDUMP_TEMP_LOG_BIN;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-12-22  0:16:33
