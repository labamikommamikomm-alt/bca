from odoo import models, api

class ReportExportVendorBill(models.AbstractModel):
    _name = "report.breeze_distribution.report_export_vendor_bill_template"
    _description = "Export Vendor Bills to PDF"

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data or not data.get('active_ids'):
            active_ids = self.env.context.get('active_ids')
        else:
            active_ids = data['active_ids']
        
        docs = self.env['account.move'].browse(active_ids)
        
        # Compute date range
        invoice_dates = docs.mapped('invoice_date')
        date_from = min(invoice_dates) if invoice_dates and any(invoice_dates) else False
        date_to = max(invoice_dates) if invoice_dates and any(invoice_dates) else False

        # Prepare context data to map properly to QWeb execution
        form_data = data and data.get('form', {}) or {}
        
        return {
            'docs': docs,
            'data': form_data,
            'company': self.env.user.company_id,
            'date_from': date_from,
            'date_to': date_to,
        }
