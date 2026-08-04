"""Create the Number Cards and Dashboard Chart the AgriSmart workspace renders.

Workspaces sync from JSON on migrate, but the widgets they *point at* are
ordinary documents and have to be created. Without this the workspace loads
with four empty boxes where the KPIs should be.

Idempotent — safe to re-run.
"""

import json

import frappe

NUMBER_CARDS = [
	{
		"name": "Open Leads",
		"label": "Open Leads",
		"filters_json": json.dumps(
			[["Pond Project", "stage", "in", ["Lead", "Qualified", "Surveyed", "Quoted"]]]
		),
		"function": "Count",
		"color": "#7575ff",
	},
	{
		"name": "Orders Booked",
		"label": "Orders Booked",
		"filters_json": json.dumps(
			[["Pond Project", "stage", "in", ["Order Booked", "Dispatched", "Delivered"]]]
		),
		"function": "Count",
		"color": "#ffa00a",
	},
	{
		"name": "Awaiting Installation",
		"label": "Awaiting Installation",
		"filters_json": json.dumps(
			[["Pond Project", "stage", "in", ["Delivered", "Installing"]]]
		),
		"function": "Count",
		"color": "#29cd42",
	},
	{
		"name": "Completed This Month",
		"label": "Completed This Month",
		"filters_json": json.dumps(
			[
				["Pond Project", "stage", "in", ["Completed", "Commission Claimed", "Closed"]],
				["Pond Project", "installation_end", "Timespan", "this month"],
			]
		),
		"function": "Sum",
		"aggregate_function_based_on": "area_sqm",
		"color": "#449cf0",
	},
]

CHART = {
	"name": "Pond Projects by Stage",
	"chart_name": "Pond Projects by Stage",
	"chart_type": "Group By",
	"group_by_type": "Count",
	"group_by_based_on": "stage",
	"document_type": "Pond Project",
	"type": "Bar",
	"filters_json": json.dumps([["Pond Project", "stage", "!=", "Lost"]]),
	"timespan": "Last Year",
	"time_interval": "Monthly",
}


def execute():
	create_number_cards()
	create_chart()
	frappe.db.commit()


def create_number_cards():
	for card in NUMBER_CARDS:
		if frappe.db.exists("Number Card", card["name"]):
			continue
		doc = frappe.new_doc("Number Card")
		doc.update(card)
		doc.document_type = "Pond Project"
		doc.type = "Document Type"
		doc.module = "AgriSmart"
		doc.is_public = 1
		doc.show_percentage_stats = 1
		doc.stats_time_interval = "Monthly"
		doc.insert(ignore_permissions=True)


def create_chart():
	if frappe.db.exists("Dashboard Chart", CHART["name"]):
		return
	doc = frappe.new_doc("Dashboard Chart")
	doc.update(CHART)
	doc.module = "AgriSmart"
	doc.is_public = 1
	doc.insert(ignore_permissions=True)
