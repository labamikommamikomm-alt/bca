from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, UserError
import json


class ReportPiutang(models.AbstractModel):
    _name = 'report.breeze_distribution.report_rekap_piutang'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(
                _("Form content is missing, this report cannot be printed."))
        model = self.env.context.get('active_model') or 'report.rekap_piutang'
        docs = self.env[model].browse(self.env.context.get('active_ids', [])) if model else []
        # form_data = data['form']
        # raise ValidationError(data['form']['from_date'])

        domain = [
            ('journal_id.type', '=', 'sale'),
            ('invoice_date', '>=', data['form']['date_from']),
            ('invoice_date', '<=', data['form']['date_to'])
        ]
        
        if data['form'].get('team_id'):
            domain.append(('team_id', '=', data['form']['team_id'][0] if isinstance(data['form']['team_id'], list) else data['form']['team_id']))
            
        if data['form'].get('partner_id'):
            domain.append(('partner_id', '=', data['form']['partner_id'][0] if isinstance(data['form']['partner_id'], list) else data['form']['partner_id']))
            
        state_filter = data['form'].get('payment_state', 'all')
        if state_filter != 'all':
            domain.append(('payment_state', '=', state_filter))

        invoice = self.env['account.move'].search(domain)
        
        company = self.env['res.company'].sudo().search([])

        company_name = self.env.company.name
        
        team_id = data['form'].get('team_id')
        if team_id:
            team_id = team_id[0] if isinstance(team_id, list) else team_id
            data['form']['team_name'] = self.env['crm.team'].browse(team_id).name
        partner_id = data['form'].get('partner_id')
        if partner_id:
            partner_id = partner_id[0] if isinstance(partner_id, list) else partner_id
            data['form']['partner_name'] = self.env['res.partner'].browse(partner_id).name

        rows = {}
        for rec in invoice:
            rows[rec.id] = {
                'tanggal_faktur': rec.invoice_date,
                'no_faktur': rec.name,
                'customer': rec.partner_id.name,
                'jumlah': rec.amount_total,
                'terbayar': rec.amount_total - rec.amount_residual,
                'sisa': rec.amount_residual,
                'wilayah': rec.partner_id.city,
                'sales': rec.team_id.name or '',
                'keterangan': rec.payment_state,
                'currency_id': rec.currency_id
            }
        lines = []
        total_piutang = 0
        total_terbayar = 0
        total_sisa = 0
        
        for i in rows:
            line = rows[i]
            lines.append(line)
            total_piutang += line['jumlah']
            total_terbayar += line['terbayar']
            total_sisa += line['sisa']

        # raise ValidationError(json.dumps(lines))
        return {
          'lines': lines,
          'doc_ids': docids,
          'company_name': company_name,
          'docs': docs,
          'data': data['form'],
          'total_piutang': total_piutang,
          'total_terbayar': total_terbayar,
          'total_sisa': total_sisa,
          'currency_id': self.env.company.currency_id,
        }

        
