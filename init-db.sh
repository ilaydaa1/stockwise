# StockWise PostgreSQL initialization script
CREATE DATABASE stockwise;
CREATE USER stockwise WITH PASSWORD 'stockwise_local_password';
GRANT ALL PRIVILEGES ON DATABASE stockwise TO stockwise;
