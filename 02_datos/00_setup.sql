-- 00_setup.sql · Tarea 0.4: estructura base de Unity Catalog
-- El catálogo rag_normativa se crea desde la interfaz (Free Edition usa Default Storage).

USE CATALOG rag_normativa;

CREATE SCHEMA IF NOT EXISTS bronze COMMENT 'Datos en bruto: documentos de normativa originales';
CREATE SCHEMA IF NOT EXISTS silver COMMENT 'Texto extraído, limpio y troceado en chunks';
CREATE SCHEMA IF NOT EXISTS gold   COMMENT 'Tablas listas para Vector Search y evaluación';

CREATE VOLUME IF NOT EXISTS bronze.originales COMMENT 'PDF originales de normativa';

-- Comprobación
SHOW SCHEMAS IN rag_normativa;
SHOW VOLUMES IN rag_normativa.bronze;