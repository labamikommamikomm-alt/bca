
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class AssignInvoiceToSales(models.Model):
    _name = 'breeze_distribution.assign'
    _description = 'Assign Sales'
    _rec_name = 'sales_id'


    invoice_id = fields.Many2many('account.move', string='Invoice')
    sales_id = fields.Many2one('crm.team', string='Sales Person')
    tanggal = fields.Date(string="Tanggal")
    # sales_id = fields.Many2one('res.users', string='Sales Person', ondelete='set default')

    @api.onchange("sales_id")
    def invoice(self):
        res = {}
        linstInvoice = []
        assign = self.env['breeze_distribution.assign'].search([])

        for record in assign:
            for invoice in record.invoice_id:
                linstInvoice.append(invoice.id)

        res['domain'] = {'invoice_id': [('id', 'not in', linstInvoice), '|', ('payment_state', '=', 'not_paid'), (
            'payment_state', '=', 'partial'), ('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]}
        return res


    @api.model
    def create(self , vals):
        for record in vals['invoice_id'][0][2]:
            inv = self.env['account.move'].search([('id', '=', record)])
            
            inv.team_id = vals['sales_id']
        
        return super(AssignInvoiceToSales, self).create(vals)


    # def write(self, vals):
    #     # raise ValidationError(vals['sales_id'])
    #     for record in vals['invoice_id'][0][2]:
    #         inv = self.env['account.move'].search([('id', '=', record)])
            
    #         inv.team_id = vals['sales_id']
    #     return super(AssignInvoiceToSales, self).write(vals)


