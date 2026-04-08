from odoo import api, models, fields
from odoo.exceptions import UserError


class ReportRekapPembayaranPiutang(models.AbstractModel):
    _name = 'report.breeze_distribution.report_rekap_pembayaran_piutang'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError("Form content is missing, this report cannot be printed.")

        form = data['form']
        date_from = form.get('date_from')
        date_to = form.get('date_to')
        payment_date_from = form.get('payment_date_from')
        payment_date_to = form.get('payment_date_to')
        user_id = form.get('user_id')
        journal_id = form.get('journal_id')

        # Find relevant payments based on filters
        payment_domain = [('payment_type', '=', 'inbound')]
        if payment_date_from:
            payment_domain.append(('date', '>=', payment_date_from))
        if payment_date_to:
            payment_domain.append(('date', '<=', payment_date_to))
        if journal_id:
            payment_domain.append(('journal_id', '=', journal_id))

        payments = self.env['account.payment'].search(payment_domain)

        # Map payments to the invoices they pay
        # and respect Invoice Date and Salesperson/Kolektor filters
        
        # A payment can be linked to multiple invoices via reconciled lines
        invoice_ids = set()
        payment_moves = payments.mapped('move_id')
        reconciled_lines = payment_moves.mapped('line_ids.matched_debit_ids.debit_move_id.move_id') | \
                           payment_moves.mapped('line_ids.matched_credit_ids.credit_move_id.move_id')
        
        invoices = reconciled_lines.filtered(lambda m: m.move_type in ('out_invoice', 'out_refund'))

        # Apply invoice filters
        if date_from:
            invoices = invoices.filtered(lambda i: i.invoice_date and i.invoice_date >= fields.Date.from_string(date_from))
        if date_to:
            invoices = invoices.filtered(lambda i: i.invoice_date and i.invoice_date <= fields.Date.from_string(date_to))
        if user_id:
            invoices = invoices.filtered(lambda i: i.invoice_user_id.id == user_id)

        # Structure data grouping by salesperson / kolektor (using 'penagih' in the template)
        grouped_data = {}
        company = self.env.company
        currency_id = company.currency_id

        for inv in invoices:
            penagih_name = inv.invoice_user_id.name or 'Unknown'
            if penagih_name not in grouped_data:
                grouped_data[penagih_name] = {
                    'penagih': penagih_name,
                    'lines': [],
                    'total_admin': 0.0,
                    'total_saldo': 0.0,
                    'total_ppn': 0.0,
                    'total_pph': 0.0,
                    'total_bayar': 0.0,
                }
            
            # Find specific payments for this invoice
            inv_reconciled_lines = inv.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
            # payments for this invoice
            inv_payments = inv_reconciled_lines.mapped('matched_credit_ids.credit_move_id.payment_id') | \
                           inv_reconciled_lines.mapped('matched_debit_ids.debit_move_id.payment_id')
                           
            # Further filter payments by the original filter criteria
            valid_payments = inv_payments.filtered(lambda p: p in payments)
            if not valid_payments and (payment_date_from or payment_date_to or journal_id):
                # If filters were applied but this invoice's payments don't match, skip it
                continue
                
            bayar_amount = sum(valid_payments.mapped('amount'))
            tgl_lunas = valid_payments.mapped('date')
            jenis = valid_payments.mapped('journal_id.name')

            line_data = {
                'faktur': inv.name,
                'tanggal': inv.invoice_date,
                'customer': inv.partner_id.name,
                'sales': inv.invoice_user_id.name,
                'tgl_lunas': tgl_lunas,
                'keterangan': inv.payment_state,
                'jenis': jenis,
                'taxes': [], # To be calculated if needed, placeholder for now
                'saldo': inv.amount_total,
                'ppn': inv.amount_tax,
                'bayar': bayar_amount,
            }

            grouped_data[penagih_name]['lines'].append(line_data)
            grouped_data[penagih_name]['total_saldo'] += inv.amount_total
            grouped_data[penagih_name]['total_ppn'] += inv.amount_tax
            grouped_data[penagih_name]['total_bayar'] += bayar_amount

        lines_result = list(grouped_data.values())
        if user_id:
            form['user_name'] = self.env['res.users'].browse(user_id).name
        if journal_id:
            form['journal_name'] = self.env['account.journal'].browse(journal_id).name

        return {
            'doc_ids': docids,
            'doc_model': 'report.rekap_pembayaran_piutang',
            'data': form,
            'lines': lines_result,
            'company_name': company.name,
            'currency_id': currency_id,
        }
