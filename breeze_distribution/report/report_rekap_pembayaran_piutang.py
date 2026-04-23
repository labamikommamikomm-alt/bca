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
        team_id = form.get('team_id')
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
        if team_id:
            invoices = invoices.filtered(lambda i: i.team_id.id == team_id)

        # Structure data grouping by salesperson / kolektor (using 'penagih' in the template)
        grouped_data = {}
        company = self.env.company
        currency_id = company.currency_id

        # Collect dynamic global tax names first
        dynamic_tax_names = set()
        for inv in invoices:
            for t in inv.global_tax_ids:
                if t.global_tax_id.name:
                    dynamic_tax_names.add(t.global_tax_id.name)
        dynamic_tax_names = sorted(list(dynamic_tax_names))

        for inv in invoices:
            penagih_name = inv.team_id.name or 'Unknown'
            if penagih_name not in grouped_data:
                grouped_data[penagih_name] = {
                    'penagih': penagih_name,
                    'lines': [],
                    'total_saldo': 0.0,
                    'total_bayar': 0.0,
                    'total_taxes': {tax: 0.0 for tax in dynamic_tax_names},
                }
            
            # Find specific payments for this invoice
            inv_reconciled_lines = inv.line_ids.filtered(lambda l: l.account_id.user_type_id.type == 'receivable')
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

            # Process Global Taxes
            global_taxes = inv.global_tax_ids
            # Leave PPN separately only for saldo calculation if we desire (saldo = total + PPN)
            ppn_val = sum(global_taxes.filtered(lambda t: t.global_tax_id.name and 'PPN' in t.global_tax_id.name.upper()).mapped('amount'))
            
            # Saldo = total + ppn
            saldo_val = inv.amount_total + ppn_val

            line_taxes = {tax: 0.0 for tax in dynamic_tax_names}
            for t in global_taxes:
                if t.global_tax_id.name:
                    line_taxes[t.global_tax_id.name] += t.amount

            line_data = {
                'faktur': inv.name,
                'tanggal': inv.invoice_date,
                'customer': inv.partner_id.name,
                'sales': inv.team_id.name,
                'tgl_lunas': tgl_lunas,
                'keterangan': ', '.join(jenis) if jenis else '',
                'jenis': jenis,
                'saldo': saldo_val,
                'taxes': line_taxes,
                'bayar': bayar_amount,
            }

            grouped_data[penagih_name]['lines'].append(line_data)
            grouped_data[penagih_name]['total_saldo'] += saldo_val
            grouped_data[penagih_name]['total_bayar'] += bayar_amount
            for tax in dynamic_tax_names:
                grouped_data[penagih_name]['total_taxes'][tax] += line_taxes[tax]

        lines_result = list(grouped_data.values())
        
        # Calculate Grand Totals
        grand_total_saldo = sum(x['total_saldo'] for x in lines_result)
        grand_total_bayar = sum(x['total_bayar'] for x in lines_result)
        grand_total_taxes = {tax: sum(x['total_taxes'][tax] for x in lines_result) for tax in dynamic_tax_names}

        if team_id:
            form['team_name'] = self.env['crm.team'].browse(team_id).name
        if journal_id:
            form['journal_name'] = self.env['account.journal'].browse(journal_id).name

        return {
            'doc_ids': docids,
            'doc_model': 'report.rekap_pembayaran_piutang',
            'data': form,
            'lines': lines_result,
            'company_name': company.name,
            'currency_id': currency_id,
            'grand_total_saldo': grand_total_saldo,
            'grand_total_taxes': grand_total_taxes,
            'grand_total_bayar': grand_total_bayar,
            'dynamic_tax_names': dynamic_tax_names,
        }
