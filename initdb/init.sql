USE mydatabase;

CREATE TABLE IF NOT EXISTS airQuality (
    id INT AUTO_INCREMENT PRIMARY KEY,
    -- DateTime DATETIME NOT NULL,
    strDatetime VARCHAR(16),
    ms BIGINT,
    VOC INT,
    CO2 INT,
    CH2O FLOAT,
    eVOC INT,
    Humid FLOAT,
    Temp FLOAT,
    `PM2.5` FLOAT,
    `PM10` FLOAT,
    CO FLOAT
);
