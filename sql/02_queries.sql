USE supply_chain;

-- Task 1: Calculate total inventory
SELECT SUM(wi.QuantityOnHand) AS total_units_on_hand,
       ROUND(SUM(wi.QuantityOnHand * rm.UnitCost), 2) AS total_stock_value
FROM warehouse_inventory wi
JOIN raw_materials rm ON rm.MaterialID = wi.MaterialID;


-- Task 2: Find products with low stock
-- The data has no reorder level, so "low" means: below 50% of that material's average across warehouses
WITH positions AS (
    SELECT rm.MaterialName, w.WarehouseName, wi.QuantityOnHand,
           AVG(wi.QuantityOnHand) OVER (PARTITION BY wi.MaterialID) AS material_avg
    FROM warehouse_inventory wi
    JOIN raw_materials rm ON rm.MaterialID = wi.MaterialID
    JOIN warehouses w ON w.WarehouseID = wi.WarehouseID
)
SELECT MaterialName, WarehouseName, QuantityOnHand,
       ROUND(material_avg, 0) AS material_avg,
       ROUND(QuantityOnHand / material_avg * 100, 1) AS pct_of_avg
FROM positions
WHERE QuantityOnHand < 0.5 * material_avg
ORDER BY pct_of_avg;


-- Task 3: Calculate supplier-wise orders
SELECT s.SupplierName,
       COUNT(*) AS purchase_orders,
       SUM(po.Status = 'Cancelled') AS cancelled,
       ROUND(SUM(po.Status = 'Cancelled') / COUNT(*) * 100, 1) AS cancel_rate_pct
FROM purchase_orders po
JOIN suppliers s ON s.SupplierID = po.SupplierID
GROUP BY s.SupplierName
ORDER BY purchase_orders DESC;


-- Task 5: Analyze warehouse inventory
SELECT w.WarehouseName, w.location,
       SUM(wi.QuantityOnHand) AS units_on_hand,
       ROUND(SUM(wi.QuantityOnHand * rm.UnitCost), 2) AS stock_value,
       ROUND(SUM(wi.QuantityOnHand) / SUM(SUM(wi.QuantityOnHand)) OVER () * 100, 1) AS share_of_units_pct
FROM warehouse_inventory wi
JOIN warehouses w ON w.WarehouseID = wi.WarehouseID
JOIN raw_materials rm ON rm.MaterialID = wi.MaterialID
GROUP BY w.WarehouseName, w.location
ORDER BY units_on_hand DESC;


-- Task 7: Rank suppliers based on order quantity
SELECT RANK() OVER (ORDER BY SUM(pol.Quantity) DESC) AS supplier_rank,
       s.SupplierName,
       SUM(pol.Quantity) AS units_ordered,
       ROUND(SUM(pol.LineTotal), 2) AS spend
FROM purchase_order_lines pol
JOIN purchase_orders po ON po.PO_ID = pol.PO_ID
JOIN suppliers s ON s.SupplierID = po.SupplierID
GROUP BY s.SupplierName
ORDER BY supplier_rank;


-- Task 4a: Delayed shipments by carrier
-- (no delivery dates exist, so "delayed" = shipment Status 'Delayed')
SELECT COALESCE(c.CarrierName, 'Unknown') AS carrier,
       COUNT(*) AS shipments,
       SUM(st.Status = 'Delayed') AS delayed_count,
       ROUND(SUM(st.Status = 'Delayed') / COUNT(*) * 100, 1) AS delayed_pct
FROM shipment_tracking st
LEFT JOIN carriers c ON c.CarrierID = st.CarrierID
WHERE st.Status <> 'Unknown'
GROUP BY carrier
ORDER BY delayed_pct DESC;


-- Task 4b: Delayed shipments by origin warehouse
SELECT COALESCE(w.WarehouseName, 'Unknown') AS origin_warehouse,
       COUNT(*) AS shipments,
       SUM(st.Status = 'Delayed') AS delayed_count,
       ROUND(SUM(st.Status = 'Delayed') / COUNT(*) * 100, 1) AS delayed_pct
FROM shipment_tracking st
LEFT JOIN warehouses w ON w.WarehouseID = st.OriginWarehouseID
WHERE st.Status <> 'Unknown'
GROUP BY origin_warehouse
ORDER BY delayed_pct DESC;


-- Task 6: Average delivery time
-- (no actual delivery dates, so we use planned lead time: expected delivery minus order date)
SELECT s.SupplierName,
       ROUND(AVG(DATEDIFF(po.ExpectedDeliveryDate, po.OrderDate)), 1) AS avg_planned_lead_days,
       sp.AverageLeadTime_Days AS lead_days_in_supplier_table
FROM purchase_orders po
JOIN suppliers s ON s.SupplierID = po.SupplierID
JOIN supplier_performance sp ON sp.SupplierID = s.SupplierID
WHERE po.ExpectedDeliveryDate IS NOT NULL
GROUP BY s.SupplierName, sp.AverageLeadTime_Days
ORDER BY avg_planned_lead_days DESC;


-- Task 8: Monthly order trends (sales orders, with month-over-month change)
WITH monthly AS (
    SELECT DATE_FORMAT(OrderDate, '%Y-%m') AS ym,
           COUNT(*) AS orders,
           SUM(Quantity) AS units
    FROM sales_orders
    GROUP BY ym
)
SELECT ym, orders, units,
       ROUND((units - LAG(units) OVER (ORDER BY ym)) / LAG(units) OVER (ORDER BY ym) * 100, 1) AS units_change_pct
FROM monthly
ORDER BY ym;


-- Task 9: Calculate product demand
SELECT ProductName,
       COUNT(*) AS orders,
       SUM(Quantity) AS units_demanded,
       ROUND(SUM(Quantity) / SUM(SUM(Quantity)) OVER () * 100, 1) AS share_pct
FROM sales_orders
GROUP BY ProductName
ORDER BY units_demanded DESC;


-- Task 10: Warehouse utilization (capacity values are ASSUMED)
ALTER TABLE warehouses ADD COLUMN CapacityUnits INT;

UPDATE warehouses
SET CapacityUnits = CASE WarehouseID
        WHEN 'WH-A' THEN 30000
        WHEN 'WH-E' THEN 25000
        WHEN 'WH-N' THEN 25000
    END
WHERE WarehouseID IN ('WH-A', 'WH-E', 'WH-N');

SELECT w.WarehouseName, w.CapacityUnits,
       SUM(wi.QuantityOnHand) AS units_on_hand,
       ROUND(SUM(wi.QuantityOnHand) / w.CapacityUnits * 100, 1) AS utilization_pct
FROM warehouses w
JOIN warehouse_inventory wi ON wi.WarehouseID = w.WarehouseID
GROUP BY w.WarehouseName, w.CapacityUnits
ORDER BY utilization_pct DESC;