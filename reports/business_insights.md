# Business Insights - Supply Chain and Inventory Analytics Report

Prepared by Rakhi Mete, 12 November 2026

## Executive summary

This report analyses procurement, inventory, shipping and demand data for a supply chain with 4 suppliers, 4 raw materials and 3 warehouses. Ghana Cocoa Beans drives 57.7% of procurement spend, and Ghana Cocoa Beans makes up 40.5% of stock value. About 25.1% of shipments are delayed across the whole network and 22.9% of purchase orders are cancelled. Demand is steady, so the main opportunities are stock rebalancing, supplier management and better delivery-date tracking.

## Insights and recommendations

**1. Procurement spend is concentrated in one material**

Ghana Cocoa Beans accounts for 57.7% of total procurement spend.

*Recommendation:* Focus negotiation, dual sourcing and price monitoring on this material first.

**2. A high-value material is thin in some warehouses**

Ghana Cocoa Beans is 40.5% of stock value but only 13.6% of units. The lowest stock position is Ghana Cocoa Beans at Euro Hub (625 units).

*Recommendation:* Set reorder points for the lowest positions and rebalance stock between warehouses.

**3. Stock is unevenly spread across warehouses**

Asia-Pacific Hub holds 43.0% of all units on hand, while North America Hub holds 28.0%.

*Recommendation:* Review inter-warehouse transfers so stock sits close to where it is needed.

**4. Suppliers trade off reliability, speed and quality**

Packaging Pros has the lowest on-time rate (87.7%), while Global Sweeteners has the highest (98.8%). Global Sweeteners lists the longest lead time (35 days). Packaging Pros has the best quality score (4.78). PO cancellations range from 16.1% (Packaging Pros) to 27.2% (Dairy Farms United); overall 22.9%. Planned PO lead time averages 29.4 days, which does not match the supplier table. No quality score is recorded for: Global Sweeteners.

*Recommendation:* Build a supplier scorecard, collect missing quality data and align planned lead times with actual performance.

**5. Shipment delays are network-wide, not tied to one carrier or warehouse**

About 25.1% of shipments are marked Delayed. The rate ranges only from 25.0% to 25.9% across carriers and 23.5% to 25.9% across origin warehouses.

*Recommendation:* Capture actual delivery dates so delay causes can be measured properly.

**6. Demand is stable with modest growth**

Average monthly units demanded: 2024: 12,803, 2025: 13,468, 2026: 13,631 (+6.5% from first to last year). Product shares range from 23.1% to 26.6%, led by Enchanted Milk Chocolate.

*Recommendation:* A steady reorder policy fits this demand; large seasonal buffers are not needed.

## Data limitations

- The dataset is synthetic (generated), so patterns are weaker than in real operational data.
- Shipment dates are not linked to order dates, and there are no delivery dates; delays use shipment status only.
- All stock movements are inbound, so inventory turnover cannot be calculated.
- Only a few suppliers, materials and warehouses exist, so rankings are indicative.
- The last month of sales data is partial and was excluded from monthly averages.