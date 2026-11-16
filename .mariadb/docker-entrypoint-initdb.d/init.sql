/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

CREATE DATABASE IF NOT EXISTS `JurySystem` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci */;
USE `JurySystem`;

CREATE TABLE IF NOT EXISTS `users` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `username` varchar(50) DEFAULT NULL,
  `hash` varchar(500) DEFAULT NULL,
  `email` varchar(50) DEFAULT NULL,
  `team` varchar(50) DEFAULT NULL,
  `registered` datetime DEFAULT NULL,
  `expires` datetime DEFAULT NULL,
  `restrictions` tinyint(4) DEFAULT NULL,
  `locked` tinyint(4) DEFAULT NULL,
  `hidden` tinyint(4) DEFAULT 0,
  `token` varchar(50) DEFAULT '',
  `language`varchar(2) DEFAULT 'ge',
  PRIMARY KEY (`id`),
  UNIQUE (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `athletes` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `givenname` varchar(50) DEFAULT NULL,
  `surname` varchar(50) DEFAULT NULL,
  `userId` int(10) unsigned NOT NULL,
  `birth` datetime DEFAULT NULL,
  `gender` tinyint(4) DEFAULT NULL,
  `hidden` tinyint(4) DEFAULT 0,
  PRIMARY KEY (`id`),
  FOREIGN KEY (`userId`) REFERENCES users(`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `athletes` (`id`, `givenname`, `surname`, `userId`, `birth`, `gender`, `hidden`) VALUES
  (1, 'Klaus', 'Stocker', 3, '1978-07-15', 0, 0),
  (2, 'Christoph', 'Hogl', 4, '1977-07-13', 0, 0),
  (3, 'Johanna', 'Stocker', 3, '2010-05-20', 1, 0),
  (4, 'Herbet', 'Mayer', 4, '2010-05-20', 0, 0),
  (5, 'Sophia', 'Mayer', 4, '2010-05-20', 1, 0),
  (6, 'Stocker', 'Daniel', 3, '2015-03-31', 0, 0);

CREATE TABLE IF NOT EXISTS `events` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `userId` int(10) unsigned NOT NULL,
  `date` datetime NOT NULL,
  `finished`tinyint(4) DEFAULT 0,
  `deleted` tinyint(4) DEFAULT 0,
  `customRanking` VARCHAR(500) NOT NULL DEFAULT '',
  PRIMARY KEY (`id`),
  FOREIGN KEY (`userId`) REFERENCES users(`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `events` (`id`, `name`, `userId`, `date`, `finished`, `deleted`, `customRanking`) VALUES
  (1, 'Bezirksmeisterschaften 2025', 2, '2025-05-28', 1, 0, 'goldThres, silberThres, bronzeThres = 30, 20, 10'),
  (2, 'Bezirksmeisterschaften 2026', 2, '2026-05-28', 0, 0, 'goldThres, silberThres, bronzeThres = 30, 20, 10');

CREATE TABLE IF NOT EXISTS `event_judges` (
  `eventId` int(10) unsigned NOT NULL,
  `userId` int(10) unsigned NOT NULL,
  PRIMARY KEY (`eventId`, `userId`),
  FOREIGN KEY (`eventId`) REFERENCES events(`id`),
  FOREIGN KEY (`userId`) REFERENCES users(`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `event_judges` (`eventId`, `userId`) VALUES
  (1, 5);

CREATE TABLE IF NOT EXISTS `event_categories` (
  `name` varchar(50) NOT NULL,
  `eventId` int(10) unsigned NOT NULL,
  `gender` tinyint(4) NOT NULL,
  `birthFrom` datetime NOT NULL,
  `birthTo` datetime NOT NULL,
  `rankingType` tinyint(4),
  `rankingAlgo` varchar(500),
  PRIMARY KEY (`name`, `eventId`),
  FOREIGN KEY (`eventId`) REFERENCES events(`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `event_categories` (`name`, `eventId`, `gender`, `birthFrom`, `birthTo`, `rankingType`, `rankingAlgo`) VALUES
  ('Kn01', 1, 0, '1900-01-01', '2000-12-31', 0, ''),
  ('Kn02', 1, 0, '2000-01-01', '2099-12-31', 0, ''),
  ('Md01', 1, 1, '1900-01-01', '2099-12-31', 1, '"gold" if sum > goldThres else "silber" if sum > silberThres else "bronze" if sum > bronzeThres else ""');

CREATE TABLE IF NOT EXISTS `event_disciplines` (
  `name` varchar(50) NOT NULL,
  `eventId` int(10) unsigned NOT NULL,
  PRIMARY KEY (`name`, `eventId`),
  FOREIGN KEY (`eventId`) REFERENCES events(`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `event_disciplines` (`name`, `eventId`) VALUES
  ('Reck', 1),
  ('Boden', 1),
  ('Sprung', 1),
  ('Barren/Balken', 1);

CREATE TABLE IF NOT EXISTS `attendances` (
  `athleteId` int(10) unsigned NOT NULL,
  `eventId` int(10) unsigned NOT NULL,
  `eventCategoryName` varchar(50) NOT NULL,
  `bib` int(10) unsigned DEFAULT NULL,
  `group` varchar(50) NOT NULL,
  `hidden` tinyint(4) DEFAULT 0,
  PRIMARY KEY (`athleteId`, `eventId`, `eventCategoryName`),
  UNIQUE (`eventId`, `bib`),
  FOREIGN KEY (`eventId`) REFERENCES events(`id`),
  FOREIGN KEY (`athleteId`) REFERENCES athletes(`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `attendances` (`athleteId`, `eventId`, `eventCategoryName`, `bib`, `group`, `hidden`) VALUES
  (1, 1, 'Kn01', 1, 'Riege1', 0),
  (2, 1, 'Kn01', 2, 'Riege1', 0),
  (4, 1, 'Kn01', 3, 'Riege2', 0),
  (3, 1, 'Md01', 4, 'Riege2', 0);

CREATE TABLE IF NOT EXISTS `ratings` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `ts` datetime NOT NULL,
  `athleteId` int(10) unsigned NOT NULL,
  `eventDisciplineName` varchar(50) NOT NULL,
  `eventId` int(10) unsigned NOT NULL,
  `userId` int(10) unsigned NOT NULL,
  `difficulty` decimal(8,4) NOT NULL,
  `execution` decimal(8,4) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE (`athleteId`, `eventId`, `eventDisciplineName`),
  FOREIGN KEY (`eventId`) REFERENCES events(`id`),
  FOREIGN KEY (`athleteId`) REFERENCES athletes(`id`),
  FOREIGN KEY (`userId`) REFERENCES users(`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `ratings` (`id`, `ts`, `athleteId`, `eventDisciplineName`, `eventId`, `userId`, `difficulty`, `execution`) VALUES
  (1, '2025-05-25', 1, 'Reck', 1, 5, 6.7, 2.0),
  (2, '2025-05-25', 2, 'Reck', 1, 5, 5.7, 1.0),
  (3, '2025-05-25', 1, 'Boden', 1, 5, 4.0, 2.0),
  (4, '2025-05-25', 2, 'Boden', 1, 5, 6.0, 2.0),
  (5, '2025-05-25', 4, 'Sprung', 1, 5, 6.0, 2.0);

-- photos with recognized start numbers, one row per bib on the photo
-- (eventId, bib) is not unique here: one athlete can be on many photos
CREATE TABLE IF NOT EXISTS `pictures` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `eventId` int(10) unsigned NOT NULL,
  `bib` int(10) unsigned NOT NULL,
  `imagePath` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  KEY (`eventId`, `bib`),
  FOREIGN KEY (`eventId`) REFERENCES events(`id`),
  FOREIGN KEY (`eventId`, `bib`) REFERENCES attendances(`eventId`, `bib`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;



/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;

-- Benutzer erstellen
CREATE USER 'JurySystem'@'%' IDENTIFIED BY 'asdfuas347lkasudhr';
-- Optional: Berechtigungen gewähren
GRANT ALL PRIVILEGES ON `JurySystem`.* TO 'JurySystem'@'%' WITH GRANT OPTION;
-- Änderungen anwenden
FLUSH PRIVILEGES;

