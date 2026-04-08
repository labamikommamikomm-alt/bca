from odoo import models, fields
from odoo.exceptions import ValidationError, UserError
import json

class RekapPenjualan(models.TransientModel):
    _name = 'report.rekap_penjualan'
    
    customer_id = fields.Many2one('res.partner',string='Pembeli')
    date_from = fields.Date(string='Dari Tanggal', default=fields.Date.context_today)
    date_to = fields.Date(string='Sampai Tanggal', default=fields.Date.context_today)

    def check_report(self):
        self.ensure_one()
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': self.read(['customer_id', 'date_from', 'date_to'])[0]
        }
        # Pastikan baris di bawah ini lengkap, jangan cuma sampai '.r'
        return self.env.ref('breeze_distribution.report_rekap_penjualan_action').report_action(self, data=data)
    
    def preview_report(self):
        #raise ValidationError(json.dumps(self.read(['customer_id'])[0]))
        url = 'distribution/rekap_penjualan/preview/' + str(self.read(['customer_id'])[0]['customer_id'][0])
        return {
            'type' : 'ir.actions.act_url',
            'url' : url,
            'target' : '_blank'
        }
    