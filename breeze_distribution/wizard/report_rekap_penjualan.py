from odoo import models, fields
from odoo.exceptions import ValidationError, UserError
import json

class RekapPenjualan(models.TransientModel):
    _name = 'report.rekap_penjualan'
    
    customer_id = fields.Many2one('res.partner',string='Pembeli')
    


    def _build_comparison_context(self, data):
        result = {}
        result['customer_id'] = data['form']['customer_id']
        return result

    def check_report(self):
        data = {}
        data['form'] = self.read(['customer_id'])[0]
        comparison_context = self._build_comparison_context(data)
        data['form']['comparison_context'] = comparison_context
        # raise ValidationError(data['form']['from_date'])
        return self.env.ref('breeze_distribution.report_rekap_penjualan_action').report_action(self, data=data)
    
    def preview_report(self):
        #raise ValidationError(json.dumps(self.read(['customer_id'])[0]))
        url = 'distribution/rekap_penjualan/preview/' + str(self.read(['customer_id'])[0]['customer_id'][0])
        return {
            'type' : 'ir.actions.act_url',
            'url' : url,
            'target' : '_blank'
        }
    