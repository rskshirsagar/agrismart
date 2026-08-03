frappe.query_reports["Pond Project Register"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date" },
		{ fieldname: "stage", label: __("Stage"), fieldtype: "Select",
		  options: ["", "Lead", "Qualified", "Surveyed", "Quoted", "Order Booked",
		            "Dispatched", "Delivered", "Installing", "Completed",
		            "Commission Claimed", "Closed", "Lost"] },
		{ fieldname: "taluka", label: __("Taluka"), fieldtype: "Link",
		  options: "Pond Taluka" },
		{ fieldname: "sales_person", label: __("Sales Executive"),
		  fieldtype: "Link", options: "Sales Person" },
	],
};
