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
     f" ({growth:+.1f}% from first to last year). Product shares range from {prod_share.min():.1f}% to "
     f"{prod_share.max():.1f}%, led by {prod.idxmax()}.",
     "A steady reorder policy fits this demand; large seasonal buffers are not needed."),
]

limitations = [
    "The dataset is synthetic (generated), so patterns are weaker than in real operational data.",
    "Shipment dates are not linked to order dates, and there are no delivery dates; delays use shipment status only.",
    "All stock movements are inbound, so inventory turnover cannot be calculated.",
    "Only a few suppliers, materials and warehouses exist, so rankings are indicative.",
    "The last month of sales data is partial and was excluded from monthly averages.",
]

exec_summary = (
    f"This report analyses procurement, inventory, shipping and demand data for a supply chain with "
    f"{len(c['suppliers'])} suppliers, {len(mat)} raw materials and {len(wh)} warehouses. "
    f"{top_spend_mat} drives {top_spend_share:.1f}% of procurement spend, and {top_val_mat} makes up "
    f"{top_val_share:.1f}% of stock value. About {delayed_pct:.1f}% of shipments are delayed across the whole "
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

story += [Paragraph("5. Visualizations", h1)]
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

story += [Paragraph("6. Business Insights", h1)]
for i, (t, finding, rec) in enumerate(insights, 1):
    story += [Paragraph(f"{i}. {t}", h2), Paragraph(finding, body),
              Paragraph(f"<b>Recommendation:</b> {rec}", body), Spacer(1, 6)]

story += [Paragraph("7. Conclusion", h1),
          Paragraph("The analysis shows a stable demand pattern with the main risks in stock placement, "
                    "supplier management and delivery tracking rather than in demand volatility. "
                    "Priorities are: rebalance stock of the highest-value material, build a supplier "
                    "scorecard, and record real delivery dates so delay causes can be measured.", body),
          Spacer(1, 8), Paragraph("Data limitations", h2)]
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