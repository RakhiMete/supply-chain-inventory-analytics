USE supply_chain;

DROP TABLE IF EXISTS carriers, fulfillment_status, purchase_order_lines, purchase_orders,
    raw_materials, sales_orders, shipment_tracking, stock_movements,
    supplier_performance, suppliers, warehouse_inventory, warehouses;

CREATE TABLE suppliers (
    SupplierID   VARCHAR(10) PRIMARY KEY,
    SupplierName VARCHAR(100),
    country      VARCHAR(50)
);

CREATE TABLE warehouses (
    WarehouseID   VARCHAR(10) PRIMARY KEY,
    WarehouseName VARCHAR(100),
    location      VARCHAR(100)
);

CREATE TABLE raw_materials (
    MaterialID   VARCHAR(10) PRIMARY KEY,
    MaterialName VARCHAR(100),
    category     VARCHAR(50),
    UnitCost     DECIMAL(10,2)
);

CREATE TABLE carriers (
    CarrierID   VARCHAR(10) PRIMARY KEY,
    CarrierName VARCHAR(100)
);

CREATE TABLE supplier_performance (
    SupplierID           VARCHAR(10) PRIMARY KEY,
    SupplierName         VARCHAR(100),
    OnTimeDeliveryRate   DECIMAL(5,4),
    QualityScore         DECIMAL(4,2),
    AverageLeadTime_Days INT
);

CREATE TABLE purchase_orders (
    PO_ID                VARCHAR(20) PRIMARY KEY,
    SupplierID           VARCHAR(10),
    OrderDate            DATE,
    ExpectedDeliveryDate DATE,
    Status               VARCHAR(20),
    ReportedTotalCost    DECIMAL(12,2)
);

CREATE TABLE purchase_order_lines (
    POLineID   VARCHAR(20),
    PO_ID      VARCHAR(20),
    MaterialID VARCHAR(10),
    Quantity   INT,
    UnitCost   DECIMAL(10,2),
    LineTotal  DECIMAL(12,2)
);

CREATE TABLE sales_orders (
    SalesOrderID VARCHAR(20) PRIMARY KEY,
    OrderDate    DATE,
    ProductID    VARCHAR(10),
    ProductName  VARCHAR(100),
    Quantity     INT,
    CustomerID   VARCHAR(20)
);

CREATE TABLE shipment_tracking (
    ShipmentID         VARCHAR(20) PRIMARY KEY,
    CarrierID          VARCHAR(10),
    OriginWarehouseID  VARCHAR(10),
    DestinationAddress VARCHAR(100),
    ShipDate           DATE,
    Status             VARCHAR(20)
);

CREATE TABLE fulfillment_status (
    FulfillmentID VARCHAR(20),
    SalesOrderID  VARCHAR(20),
    ShipmentID    VARCHAR(20),
    Status        VARCHAR(20)
);

CREATE TABLE stock_movements (
    MovementID   VARCHAR(20),
    MaterialID   VARCHAR(10),
    WarehouseID  VARCHAR(10),
    MovementType VARCHAR(20),
    Quantity     INT,
    `Date`       DATE
);

CREATE TABLE warehouse_inventory (
    InventoryID       VARCHAR(20),
    MaterialID        VARCHAR(10),
    WarehouseID       VARCHAR(10),
    QuantityOnHand    INT,
    LastStocktakeDate DATE
);

SHOW TABLES;