from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, UserError
import json


class ReportHasilTagihan(models.AbstractModel):
    _name = 'report.breeze_distribution.report_rekap_hasil_tagihan'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(
                _("Form content is missing, this report cannot be printed."))
        model = self.env.context.get('active_model') or 'report.rekap_hasil_tagihan'
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        # form_data = data['form']
        # raise ValidationError(data['form']['from_date'])

        # company = self.env['res.company'].sudo().search([])
        company = self.env.user.company_id
        company_name = company.name
        currency_id = company.currency_id

        # Search for payment moves in the specified date range
        payment_domain = [
            ('date', '>=', data['form']['date_from']),
            ('date', '<=', data['form']['date_to']),
            ('journal_id.type', 'in', ('cash', 'bank')),
            ('ref', '!=', False)
        ]
        
        payment_moves = self.env['account.move'].sudo().search(payment_domain)
        
        rows = {}
        for p_move in payment_moves:
            # Find the invoices this payment relates to by checking the reference
            # Note: This checks 'ref' matches invoice name
            invoices = self.env['account.move'].sudo().search([('name', '=', p_move.ref), ('move_type', '=', 'out_invoice')])
            
            for inv in invoices:
                team_id = inv.team_id.id or 0
                if team_id not in rows:
                    rows[team_id] = {
                        'sales': inv.team_id.name or _('No Team'),
                        'cash': 0.0,
                        'transfer': 0.0,
                        'total': 0.0
                    }
                
                amount = sum(p_move.line_ids.filtered(lambda l: l.debit > 0).mapped('debit'))
                
                if p_move.journal_id.type == 'cash':
                    rows[team_id]['cash'] += amount
                elif p_move.journal_id.type == 'bank':
                    rows[team_id]['transfer'] += amount
                
                rows[team_id]['total'] += amount

        lines = list(rows.values())
        
        # Calculate Grand Totals
        grand_total_cash = sum(x['cash'] for x in lines)
        grand_total_transfer = sum(x['transfer'] for x in lines)
        grand_total_total = sum(x['total'] for x in lines)

        return {
          'lines': lines,
          'doc_ids': docids,
          'company_name': company_name,
          'docs': docs,
          'data': data['form'],
          'currency_id': currency_id,
          'total_cash': grand_total_cash,
          'total_transfer': grand_total_transfer,
          'total_total': grand_total_total,
        }
        lines = []
        
        for i in rows:
            lines.append(rows[i])

        # raise ValidationError(json.dumps(lines))
        return {
          'lines': lines,
          'doc_ids': docids,
          'company_name': company_name,
          'docs': docs,
          'data': data['form'],
          'currency_id': currency_id
        }

        
