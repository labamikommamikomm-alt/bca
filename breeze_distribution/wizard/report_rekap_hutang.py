from odoo import models, fields
from odoo.exceptions import ValidationError, UserError


class RekapHutang(models.TransientModel):
    _name = 'report.rekap_hutang'

    date_from = fields.Date(string="Starting Date")
    date_to = fields.Date(string="Ending Date")


    def _build_comparison_context(self, data):
        result = {}
        result['date_from'] = data['form']['date_from']
        result['date_to'] = data['form']['date_to']
        return result

    def check_report(self):
        data = {}
        data['form'] = self.read(['date_from', 'date_to'])[0]
        comparison_context = self._build_comparison_context(data)
        data['form']['comparison_context'] = comparison_context
        # raise ValidationError(data['form']['from_date'])
        return self.env.ref('breeze_distribution.report_rekap_hutang_action').report_action(self, data=data)