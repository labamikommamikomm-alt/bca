# peminjaman/reports/borrow_report_wizard.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import datetime

class BorrowReportWizard(models.TransientModel):
    _name = 'report.borrow.report.wizard'
    _description = 'Wizard for Peminjaman/Pengembalian Report'

    start_date = fields.Date(string="Tanggal Mulai", required=True, default=fields.Date.today())
    end_date = fields.Date(string="Tanggal Akhir", required=True, default=fields.Date.today())
    partner_id = fields.Many2one('res.partner', string="Partner", help="Kosongkan untuk semua partner.")
    report_type = fields.Selection([
        ('borrowed', 'Peminjaman'),
        ('returned', 'Pengembalian'),
        ('all', 'Semua')
    ], string="Tipe Laporan", default='all', required=True)
    show_returned_items = fields.Boolean(string="Tampilkan Barang Dikembalikan", default=True,
        help="Jika Peminjaman, centang untuk menampilkan barang yang sudah dikembalikan.")

    def check_report(self):
        data = {
            'model': self._name,
            'form': self.read(['start_date', 'end_date', 'partner_id', 'report_type', 'show_returned_items'])[0]
        }
        # Correctly pass partner_id as a tuple if it exists
        if data['form']['partner_id']:
            data['form']['partner_id'] = data['form']['partner_id']
        else:
            data['form']['partner_id'] = False # Ensure it's False if empty

        return self.env.ref('peminjaman.action_report_borrow_return').report_action(self, data=data)