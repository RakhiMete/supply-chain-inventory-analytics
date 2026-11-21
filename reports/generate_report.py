import os, glob
import pandas as pd
from datetime import date
from PIL import Image as PILImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, Image, PageBreak, KeepTogether)

AUTHOR = "Rakhi Mete"
TITLE = "Supply Chain and Inventory Analytics Report"

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW = os.path.join(BASE, "data", "raw")
CLEAN = os.path.join(BASE, "data", "cleaned")
IMG = os.path.join(BASE, "images")
OUT = os.path.join(BASE, "reports")

# ---------- 1. Load data ----------
def load(folder, parse=True):
    out = {}
    for f in sorted(glob.glob(os.path.join(folder, "*.csv"))):
        name = os.path.splitext(os.path.basename(f))[0]
        name = name[:-len("_clean")] if name.endswith("_clean") else name
        cols = pd.read_csv(f, nrows=0).columns
        dates = [col for col in cols if "date" in col.lower()] if parse else []
        out[name] = pd.read_csv(f, parse_dates=dates)
    return out

raw = load(RAW, parse=False)
c = load(CLEAN)

mat, wh = c["raw_materials"], c["warehouses"]
po, pol = c["purchase_orders"].copy(), c["purchase_order_lines"]
sales, sh = c["sales_orders"].copy(), c["shipment_tracking"]
po["PlannedLeadDays"] = (po["ExpectedDeliveryDate"] - po["OrderDate"]).dt.days

inv = (c["warehouse_inventory"]
       .merge(mat[["MaterialID", "MaterialName", "UnitCost"]], on="MaterialID")
       .merge(wh[["WarehouseID", "WarehouseName"]], on="WarehouseID"))
inv["StockValue"] = inv["QuantityOnHand"] * inv["UnitCost"]

# ---------- 2. Key facts (every number comes from the data) ----------
spend_mat = (pol.merge(mat[["MaterialID", "MaterialName"]], on="MaterialID")
             .groupby("MaterialName")["LineTotal"].sum())
top_spend_mat = spend_mat.idxmax()
top_spend_share = spend_mat.max() / spend_mat.sum() * 100

val_mat = inv.groupby("MaterialName")["StockValue"].sum()
units_mat = inv.groupby("MaterialName")["QuantityOnHand"].sum()
top_val_mat = val_mat.idxmax()
top_val_share = val_mat.max() / val_mat.sum() * 100
top_val_units_share = units_mat[top_val_mat] / units_mat.sum() * 100
low = inv.loc[inv["QuantityOnHand"].idxmin()]

wh_units = inv.groupby("WarehouseName")["QuantityOnHand"].sum()
top_wh, min_wh = wh_units.idxmax(), wh_units.idxmin()
top_wh_share = wh_units.max() / wh_units.sum() * 100
min_wh_share = wh_units.min() / wh_units.sum() * 100

st = pd.crosstab(po["SupplierID"], po["Status"])
cancel = st["Cancelled"] / st.sum(axis=1) * 100
overall_cancel = (po["Status"] == "Cancelled").mean() * 100
sup = c["suppliers"].merge(c["supplier_performance"].drop(columns="SupplierName"), on="SupplierID")
sup["CancelRate"] = sup["SupplierID"].map(cancel)
s_low = sup.loc[sup["OnTimeDeliveryRate"].idxmin()]
s_high = sup.loc[sup["OnTimeDeliveryRate"].idxmax()]
s_slow = sup.loc[sup["AverageLeadTime_Days"].idxmax()]
s_qual = sup.loc[sup["QualityScore"].idxmax()]
s_cmax = sup.loc[sup["CancelRate"].idxmax()]
s_cmin = sup.loc[sup["CancelRate"].idxmin()]
no_quality = sup[sup["QualityScore"].isna()]["SupplierName"].tolist()
planned_lead = po["PlannedLeadDays"].mean()

known = sh[sh["Status"] != "Unknown"]
delayed_pct = (known["Status"] == "Delayed").mean() * 100
car = (known[known["CarrierID"] != "Unknown"].groupby("CarrierID")["Status"]
       .apply(lambda s: (s == "Delayed").mean() * 100))
whs = (known[known["OriginWarehouseID"] != "Unknown"].groupby("OriginWarehouseID")["Status"]
       .apply(lambda s: (s == "Delayed").mean() * 100))

monthly = sales.groupby(sales["OrderDate"].dt.to_period("M"))["Quantity"].sum().iloc[:-1]  # drop partial last month
yearly = monthly.groupby(monthly.index.year).mean()
growth = (yearly.iloc[-1] / yearly.iloc[0] - 1) * 100
prod = sales.groupby("ProductName")["Quantity"].sum()
prod_share = prod / prod.sum() * 100

kpis = [
    ["Units in stock", f"{int(inv['QuantityOnHand'].sum()):,}"],
    ["Stock value", f"{inv['StockValue'].sum():,.0f}"],
    ["Procurement spend (PO lines)", f"{pol['LineTotal'].sum():,.0f}"],
    ["Suppliers / Materials / Warehouses", f"{len(c['suppliers'])} / {len(mat)} / {len(wh)}"],
    ["Purchase orders", f"{po['PO_ID'].nunique():,}"],
    ["PO cancellation rate", f"{overall_cancel:.1f}%"],
    ["Sales orders", f"{sales['SalesOrderID'].nunique():,}"],
    ["Units demanded", f"{int(sales['Quantity'].sum()):,}"],
    ["Shipments marked Delayed", f"{delayed_pct:.1f}%"],
]

# ---------- 3. Insights ----------
insights = [
    ("Procurement spend is concentrated in one material",
     f"{top_spend_mat} accounts for {top_spend_share:.1f}% of total procurement spend.",
     "Focus negotiation, dual sourcing and price monitoring on this material first."),
    ("A high-value material is thin in some warehouses",
     f"{top_val_mat} is {top_val_share:.1f}% of stock value but only {top_val_units_share:.1f}% of units. "
     f"The lowest stock position is {low['MaterialName']} at {low['WarehouseName']} "
     f"({int(low['QuantityOnHand']):,} units).",
     "Set reorder points for the lowest positions and rebalance stock between warehouses."),
    ("Stock is unevenly spread across warehouses",
     f"{top_wh} holds {top_wh_share:.1f}% of all units on hand, while {min_wh} holds {min_wh_share:.1f}%.",
     "Review inter-warehouse transfers so stock sits close to where it is needed."),
    ("Suppliers trade off reliability, speed and quality",
     f"{s_low['SupplierName']} has the lowest on-time rate ({s_low['OnTimeDeliveryRate']*100:.1f}%), "
     f"while {s_high['SupplierName']} has the highest ({s_high['OnTimeDeliveryRate']*100:.1f}%). "
     f"{s_slow['SupplierName']} lists the longest lead time ({s_slow['AverageLeadTime_Days']:.0f} days). "
     f"{s_qual['SupplierName']} has the best quality score ({s_qual['QualityScore']:.2f}). "
     f"PO cancellations range from {s_cmin['CancelRate']:.1f}% ({s_cmin['SupplierName']}) to "
     f"{s_cmax['CancelRate']:.1f}% ({s_cmax['SupplierName']}); overall {overall_cancel:.1f}%. "
     f"Planned PO lead time averages {planned_lead:.1f} days, which does not match the supplier table. "
     + (f"No quality score is recorded for: {', '.join(no_quality)}." if no_quality else ""),
     "Build a supplier scorecard, collect missing quality data and align planned lead times with actual performance."),
    ("Shipment delays are network-wide, not tied to one carrier or warehouse",
     f"About {delayed_pct:.1f}% of shipments are marked Delayed. The rate ranges only from {car.min():.1f}% to "
     f"{car.max():.1f}% across carriers and {whs.min():.1f}% to {whs.max():.1f}% across origin warehouses.",
     "Capture actual delivery dates so delay causes can be measured properly."),
    ("Demand is stable with modest growth",
     "Average monthly units demanded: " + ", ".join(f"{y}: {v:,.0f}" for y, v in yearly.items()) +
     f" ({growth:+.1f}% in monthly average from 2024 to 2026; 2026 covers Jan-Oct only). Product shares range from {prod_share.min():.1f}% to "
     f"{prod_share.max():.1f}%, led by {prod.idxmax()}.",
     "A steady reorder policy fits this demand; large seasonal buffers are not needed."),
]

limitations = [
    "The dataset is synthetic (generated), so patterns are weaker than in real operational data.",
    "Shipment dates are not linked to order dates, and there are no delivery dates; delays use shipment status only.",
    "All stock movements are inbound, so inventory turnover cannot be calculated.",
    "Only a few suppliers, materials and warehouses exist, so rankings are indicative.",
    "The last month of sales data is partial and was excluded from monthly averages.",    "Warehouse capacities (30,000 / 25,000 / 25,000 units) are assumed, so utilization figures are illustrative.",
    "Joins from orders to their lines or shipments leave out rows whose parent record was removed during cleaning, so linked spend totals are lower than totals over all order lines.",    
]

same_material = top_spend_mat == top_val_mat
material_sentence = (
    f"{top_spend_mat} drives {top_spend_share:.1f}% of procurement spend and also makes up "
    f"{top_val_share:.1f}% of stock value. " if same_material else
    f"{top_spend_mat} drives {top_spend_share:.1f}% of procurement spend, and {top_val_mat} makes up "
    f"{top_val_share:.1f}% of stock value. "
)
exec_summary = (
    f"This report analyses procurement, inventory, shipping and demand data for a supply chain with "
    f"{len(c['suppliers'])} suppliers, {len(mat)} raw materials and {len(wh)} warehouses. "
    + material_sentence +
    f"About {delayed_pct:.1f}% of shipments are delayed across the whole "
    f"network and {overall_cancel:.1f}% of purchase orders are cancelled. Demand is steady, so the main "
    f"opportunities are stock rebalancing, supplier management and better delivery-date tracking."
)

# ---------- 4. PDF ----------
ss = getSampleStyleSheet()
body = ParagraphStyle("body", parent=ss["BodyText"], fontSize=10, leading=14)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=14, bulletIndent=2)
h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontSize=16, textColor=colors.HexColor("#1F3A5F"), spaceBefore=6, spaceAfter=8)
h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12, textColor=colors.HexColor("#1F3A5F"))
cap = ParagraphStyle("cap", parent=body, fontSize=8.5, textColor=colors.grey, alignment=1)
title_style = ParagraphStyle("title", parent=ss["Title"], fontSize=26, textColor=colors.HexColor("#1F3A5F"))

def make_table(data, widths=None):
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F5F9")]),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t

def fit_image(path, max_w=16 * cm, max_h=10.5 * cm):
    w, h = PILImage.open(path).size
    s = min(max_w / w, max_h / h)
    return Image(path, width=w * s, height=h * s)

def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.drawString(2 * cm, 1.2 * cm, TITLE)
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
    canvas.restoreState()

story = [Spacer(1, 6 * cm), Paragraph(TITLE, title_style), Spacer(1, 0.5 * cm),
         Paragraph("Procurement, inventory, shipping and demand analysis",
                   ParagraphStyle("sub", parent=body, fontSize=13, alignment=1)),
         Spacer(1, 1.5 * cm),
         Paragraph(f"Prepared by: {AUTHOR}<br/>Date: {date.today():%d %B %Y}",
                   ParagraphStyle("meta", parent=body, alignment=1)), PageBreak()]

story += [Paragraph("1. Executive Summary", h1), Paragraph(exec_summary, body), Spacer(1, 8),
          Paragraph("Key figures", h2), Spacer(1, 4),
          make_table([["Metric", "Value"]] + kpis, [9 * cm, 6 * cm])]

story += [Spacer(1, 12), Paragraph("2. Dataset Overview", h1),
          Paragraph("Data was generated with the Excelx Supply Chain and Logistics Data Generator in its "
                    "slightly messy setting. It contains related tables covering procurement, inventory, "
                    "transport and order fulfillment. The cleaned tables are summarised below.", body), Spacer(1, 6)]
ov = [["Table", "Rows", "Columns"]] + [[n, f"{len(d):,}", str(d.shape[1])] for n, d in c.items()]
story += [make_table(ov, [8 * cm, 3 * cm, 3 * cm]), PageBreak()]

story += [Paragraph("3. Data Cleaning Summary", h1)]
cl = [["Table", "Raw rows", "Clean rows", "Removed", "% removed"]]
for n, d in c.items():
    r = len(raw[n]) if n in raw else len(d)
    cl.append([n, f"{r:,}", f"{len(d):,}", f"{r - len(d):,}", f"{(r - len(d)) / r * 100:.1f}%"])
story += [make_table(cl, [6 * cm, 2.6 * cm, 2.6 * cm, 2.4 * cm, 2.4 * cm]), Spacer(1, 8),
          Paragraph("Actions taken", h2)]
for t in ["Removed stray spaces from text fields and converted date columns to date type.",
          "Removed exact duplicate rows and repeated IDs.",
          "Dropped rows missing join keys (order, shipment, PO, material, supplier or warehouse IDs).",
          "Filled missing text categories with 'Unknown'; recovered product names from product IDs; restored a missing supplier from the performance table; filled missing unit costs with the material median.",
          "Dropped rows missing quantity or the main date, and rows dated in the future.",
          "Added LineTotal = Quantity x UnitCost; renamed TotalCost to ReportedTotalCost because it did not match the order lines.",
          "Left shipment and expected delivery dates blank where missing rather than inventing delays."]:
    story.append(Paragraph(t, bullet, bulletText="-"))
story.append(PageBreak())

story += [Paragraph("4. Statistical Summary", h1)]
stat = [["Measure", "Count", "Mean", "Std", "Min", "Median", "Max"]]
for label, s in [("PO line quantity", pol["Quantity"]), ("PO unit cost", pol["UnitCost"]),
                 ("PO line total", pol["LineTotal"]), ("Sales order quantity", sales["Quantity"]),
                 ("Inbound receipt quantity", c["stock_movements"]["Quantity"]),
                 ("Stock on hand per position", inv["QuantityOnHand"])]:
    stat.append([label, f"{s.count():,}", f"{s.mean():,.1f}", f"{s.std():,.1f}",
                 f"{s.min():,.1f}", f"{s.median():,.1f}", f"{s.max():,.1f}"])
story += [make_table(stat, [4.6 * cm, 1.8 * cm, 2.2 * cm, 2.2 * cm, 2 * cm, 2.2 * cm, 2.2 * cm]), PageBreak()]
# ---------- Analysis findings (tables) and SQL section ----------
cell = ParagraphStyle("cell", parent=body, fontSize=8.5, leading=11)

def text_table(data, widths):
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F5F9")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t

# Table 1: stock on hand
piv = inv.pivot_table(index="MaterialName", columns="WarehouseName", values="QuantityOnHand",
                      aggfunc="sum", margins=True, margins_name="Total")
t_stock = [["Material"] + list(piv.columns)] + [[i] + [f"{int(v):,}" for v in row] for i, row in piv.iterrows()]

# Table 2: supplier scorecard
pol_po = pol.merge(po[["PO_ID", "SupplierID"]].drop_duplicates("PO_ID"), on="PO_ID")
sup["Spend"] = sup["SupplierID"].map(pol_po.groupby("SupplierID")["LineTotal"].sum())
t_sup = [["Supplier", "On-time", "Quality", "Lead time (days)", "PO cancelled", "Spend"]]
for _, r in sup.sort_values("Spend", ascending=False).iterrows():
    t_sup.append([r["SupplierName"], f"{r['OnTimeDeliveryRate'] * 100:.1f}%",
                  "n/a" if pd.isna(r["QualityScore"]) else f"{r['QualityScore']:.2f}",
                  f"{r['AverageLeadTime_Days']:.0f}", f"{r['CancelRate']:.1f}%", f"{r['Spend']:,.0f}"])

# Table 3: shipment status mix by carrier
ct = known[known["CarrierID"] != "Unknown"].merge(c["carriers"], on="CarrierID")
mix = (pd.crosstab(ct["CarrierName"], ct["Status"], normalize="index") * 100).round(1)
t_mix = [["Carrier"] + list(mix.columns)] + [[i] + [f"{v:.1f}%" for v in row] for i, row in mix.iterrows()]

# Table 4: product demand
dem = (sales.groupby("ProductName")
       .agg(orders=("SalesOrderID", "count"), units=("Quantity", "sum"))
       .sort_values("units", ascending=False))
t_dem = [["Product", "Orders", "Units", "Share", "Avg order size"]]
for pname, r in dem.iterrows():
    t_dem.append([pname, f"{int(r['orders']):,}", f"{int(r['units']):,}",
                  f"{r['units'] / dem['units'].sum() * 100:.1f}%", f"{r['units'] / r['orders']:.1f}"])
t_dem.append(["Total", f"{int(dem['orders'].sum()):,}", f"{int(dem['units'].sum()):,}", "100.0%",
              f"{dem['units'].sum() / dem['orders'].sum():.1f}"])

story += [Paragraph("5. Analysis Findings", h1),
          Paragraph("Stock on hand by material and warehouse (units)", h2), Spacer(1, 4),
          make_table(t_stock, [4.6 * cm] + [3.1 * cm] * (len(t_stock[0]) - 1)), Spacer(1, 10),
          Paragraph("Supplier scorecard", h2), Spacer(1, 4),
          make_table(t_sup, [4.2 * cm, 2.2 * cm, 2.0 * cm, 2.8 * cm, 2.6 * cm, 3.0 * cm]),
          Paragraph("Spend counts only order lines linked to a purchase order. Quality score is not recorded for every supplier.", cap),
          Spacer(1, 10),
          Paragraph("Shipment status mix by carrier (% of shipments with a known status)", h2), Spacer(1, 4),
          make_table(t_mix, [5.2 * cm] + [2.9 * cm] * (len(t_mix[0]) - 1)), Spacer(1, 10),
          Paragraph("Product demand", h2), Spacer(1, 4),
          make_table(t_dem, [5.4 * cm, 2.6 * cm, 3.0 * cm, 2.4 * cm, 3.0 * cm]),
          PageBreak()]

# SQL section: values below were taken from the verified MySQL outputs
sql_rows = [
    ("1", "Total inventory", "54,643 units on hand; stock value 377,284."),
    ("2", "Products with low stock", "4 material-warehouse positions are below 50% of that material's average. Lowest: Ghana Cocoa Beans at the Euro Hub (625 units)."),
    ("3", "Supplier-wise orders", "Purchase orders: Dairy Farms United 279, Global Sweeteners 273, Cocoa World 261, Packaging Pros 249 (1,062 in total)."),
    ("4", "Delayed shipments", "About 25% of shipments are Delayed for every carrier (25.0%-25.9%) and origin warehouse (23.5%-25.9%)."),
    ("5", "Warehouse inventory", "Asia-Pacific 23,477 units (43.0%), Euro Hub 15,882 (29.1%), North America 15,284 (28.0%)."),
    ("6", "Average delivery time", "Planned lead time is 28.2-30.3 days for every supplier, while the supplier table lists 19-35 days."),
    ("7", "Suppliers ranked by order quantity", "1) Dairy Farms United 796,484 units; 2) Global Sweeteners 703,023; 3) Cocoa World 699,953; 4) Packaging Pros 686,105."),
    ("8", "Monthly order trends", "Peak month is January 2025: 153 orders and 16,846 units (+42.2% on the previous month)."),
    ("9", "Product demand", "Enchanted Milk Chocolate leads with 121,041 units (26.6%); all four products are between 23.1% and 26.6%."),
    ("10", "Warehouse utilization", "Asia-Pacific 78.3%, Euro Hub 63.5%, North America 61.1% (capacities are assumed)."),
]
sql_data = [["#", "SQL task", "Key result"]] + [[n, Paragraph(t, cell), Paragraph(r, cell)] for n, t, r in sql_rows]
story += [Paragraph("6. SQL Analysis", h1),
          Paragraph("The cleaned tables were loaded into MySQL and the ten required tasks were written as SQL "
                    "queries (see the sql folder of the repository). Techniques used include multi-table joins, "
                    "CTEs and window functions (RANK, LAG, AVG and SUM OVER). The results below come from the "
                    "MySQL output and were cross-checked against the Pandas analysis.", body),
          Spacer(1, 6), text_table(sql_data, [0.8 * cm, 4.4 * cm, 11.8 * cm]), Spacer(1, 8),
          Paragraph("Delivery time uses planned lead time because no actual delivery dates exist; delayed shipments "
                    "use the Status field; warehouse capacities are assumed.", cap),
          PageBreak()]

story += [Paragraph("7. Visualizations", h1)]
charts = [("01_inventory_histogram.png", "Figure 1: Inventory distribution"),
          ("02_supplier_performance.png", "Figure 2: Supplier performance"),
          ("03_warehouse_stock.png", "Figure 3: Warehouse stock by material"),
          ("04_shipping_delay_histogram.png", "Figure 4: Shipping delay and planned lead time"),
          ("05_monthly_orders.png", "Figure 5: Monthly sales orders"),
          ("06_product_demand.png", "Figure 6: Product demand"),
          ("07_inventory_boxplot.png", "Figure 7: Receipt and order quantities by material"),
          ("08_demand_vs_inventory.png", "Figure 8: Demand vs inventory received"),
          ("09_correlation_heatmap.png", "Figure 9: Correlation heatmap"),
          ("10_pair_plot.png", "Figure 10: Pair plot")]
for fn, caption in charts:
    p = os.path.join(IMG, fn)
    if os.path.exists(p):
        story.append(KeepTogether([fit_image(p), Paragraph(caption, cap), Spacer(1, 10)]))
    else:
        print("WARNING: missing chart", fn)
story.append(PageBreak())

story += [Paragraph("8. Business Insights", h1)]
for i, (t, finding, rec) in enumerate(insights, 1):
    story += [Paragraph(f"{i}. {t}", h2), Paragraph(finding, body),
              Paragraph(f"<b>Recommendation:</b> {rec}", body), Spacer(1, 6)]

story += [Paragraph("9. Conclusion", h1),
          Paragraph("The analysis shows a stable demand pattern with the main risks in stock placement, "
                    "supplier management and delivery tracking rather than in demand volatility. "
                    "Priorities are: rebalance stock of the highest-value material, build a supplier "
                    "scorecard, and record real delivery dates so delay causes can be measured.", body),
          PageBreak(), Paragraph("Data limitations", h1)]
for t in limitations:
    story.append(Paragraph(t, bullet, bulletText="-"))

pdf_path = os.path.join(OUT, "Supply_Chain_Analysis_Report.pdf")
try:
    SimpleDocTemplate(pdf_path, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                      topMargin=2 * cm, bottomMargin=2 * cm, title=TITLE, author=AUTHOR
                      ).build(story, onFirstPage=footer, onLaterPages=footer)
except PermissionError:
    raise SystemExit("\nCould not write the PDF. Close "
                     "Supply_Chain_Analysis_Report.pdf in every viewer or browser tab, then run again.")

# ---------- 5. Business insights document ----------
md = [f"# Business Insights - {TITLE}", "", f"Prepared by {AUTHOR}, {date.today():%d %B %Y}", "",
      "## Executive summary", "", exec_summary, "", "## Insights and recommendations", ""]
for i, (t, finding, rec) in enumerate(insights, 1):
    md += [f"**{i}. {t}**", "", finding, "", f"*Recommendation:* {rec}", ""]
md += ["## Data limitations", ""] + [f"- {t}" for t in limitations]
with open(os.path.join(OUT, "business_insights.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(md))

print("Created:", pdf_path)
print("Created:", os.path.join(OUT, "business_insights.md"))
