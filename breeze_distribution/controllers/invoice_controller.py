from odoo import http, _, exceptions, fields
from odoo.http import request


class InvoiceController(http.Controller):
    @http.route('/breeze_distribution/get/invoice', csrf=False, auth='user', methods=['POST'], type='json')
    def getInvoice(self, **kw):
        user = request.env.user
        employee = request.env['hr.employee'].search([
            ('user_id', '=', user.id)
        ])
        if len(employee) == 0:
            raise exceptions.ValidationError('User belum memiliki entitas employee')
        
        employee = employee[0]
        res = []
        assigns = request.env['breeze_distribution.assign'].search([('sales_id', '=', employee.id)])

        invoices = []
        for assign in assigns:
            for invoice in assign.invoice_id:

                if invoice.payment_state != 'not_paid' and invoice.payment_state != 'partial':
                    continue

                invoice_lines = []

                for line in invoice.invoice_line_ids:
                    invoice_lines.append({
                        'id': line.id,
                        'product': line.product_id.name,
                        'name': line.name,
                        'quantity': line.quantity,
                        'satuan': line.product_uom_id.name,
                        'price': line.price_unit,
                        'subtotal': line.price_subtotal,
                        'tax': line.tax_base_amount,
                        'total': line.price_total,
                    })

                invoice_object = {
                    'id': invoice.id,
                    'number' : invoice.name,
                    'customer': invoice.partner_id.name,
                    'address': {
                        'street':invoice.partner_id.street, 
                        'street2':invoice.partner_id.street2, 
                        'city':invoice.partner_id.city,
                        },
                    'due_date': invoice.invoice_date_due,
                    'total' : invoice.amount_total_signed,
                    'amount_residual' : invoice.amount_residual,
                    'payment_state': invoice.payment_state,
                    'invoice_lines': invoice_lines
                }

                res.append(invoice_object)
            return res

    @http.route('/breeze_distribution/reg/invoice', csrf=False, auth='user', methods=['POST'], type='json')
    def registerPayment(self, **kw):
        user = request.env.user

        employee = request.env['hr.employee'].search([
            ('user_id', '=', user.id)
        ])
        if len(employee) == 0:
            raise exceptions.ValidationError('User belum memiliki entitas employee')
        
        employee = employee[0]

        res = []
        assigns = request.env['breeze_distribution.assign'].search([('sales_id', '=', employee.id)])

        try:
            invoice_id = kw["invoice_id"]
        except KeyError:
            raise exceptions.ValidationError(message='`invoice_id` is required.')

        try:
            amount = kw["amount"]
        except KeyError:
            raise exceptions.ValidationError(message='`amount` is required.')

        try:
            journal_id = kw["journal_id"]
        except KeyError:
            raise exceptions.ValidationError(message='`journal_id` is required.')

        invoice = request.env['account.move'].browse([invoice_id])
        journal = request.env['account.journal'].browse([journal_id])

        payment = request.env['account.payment.register'].with_context(
                {'active_model': 'account.move',
                 'active_ids': invoice_id}
            ).create({
                'journal_id' : journal_id,
                'payment_date': fields.Date.today(),
                'amount': amount
            }).action_create_payments()

        # Buat rekap cash

        RekapTitipan = request.env['breeze_distribution.rekap_titipan'].sudo()

        metode = 'Lain-Lain'

        if journal.type == 'bank':
            metode = 'Transfer'
        if journal.type == 'cash':
            metode = 'Cash'

        RekapTitipan.create({
            'employee_id': employee.id,
            'invoice_id': invoice.id,
            'metode': metode,
            'jumlah': amount
        })

        return {
            'status':'Success',
            'message': 'Berhasil register pembayaran'
        }

    @http.route('/breeze_distribution/journals', csrf=False, auth='user', methods=['POST'], type='json')
    def getJournal(self, **kw):
        user = request.env.user

        journals = request.env['account.journal'].search([
            ('company_id', '=', user.company_id.id),
            ('type', 'in', ['bank', 'cash'])
        ])

        res = []

        for journal in journals:
            res.append({
                'id': journal.id,
                'name': journal.name
            })

        return res

    