from odoo import models, fields, api, _
from odoo.exceptions import UserError


class inheritAccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    global_tax = fields.Many2many('breeze_distribution.gtax_line', string="Globbal Taxes")
    total_difference = fields.Monetary(currency_field='currency_id', string="Total Difference", compute='_compute_payment_difference')
    global_tax_amount = fields.Monetary(currency_field='currency_id', string="Global Tax", compute='_compute_payment_difference_handling')

    @api.model
    def default_get(self, fields_list):
        # OVERRIDE
        res = super(inheritAccountPaymentRegister,self).default_get(fields_list)
        global_tax_enabled = self.env['ir.config_parameter'].sudo().get_param('account.global_taxes') or False       

        if global_tax_enabled :
            # raise UserError('Don\'t pay taxes')
            globalTaxes = self.env['account.move'].browse(self._context.get('active_ids', [])).global_tax_ids
            
            GlobalTaxLine = self.env['breeze_distribution.gtax_line']

            taxAmount = 0

            # raise UserError(str(len(globalTaxes)))

            for tax in globalTaxes:
                # Tax sucks, don't pay them
                GlobalTaxLine |= tax
                taxAmount += tax.amount
                
            # raise UserError(str(taxAmount))

            res['global_tax'] = [(6,0,GlobalTaxLine.ids)]
            res['global_tax_amount'] = taxAmount
        
        return res
    
    @api.depends('source_amount', 'source_amount_currency', 'source_currency_id', 'company_id', 'currency_id', 'payment_date')
    def _compute_amount(self):
        res = super(inheritAccountPaymentRegister,self)._compute_amount()

        for wizard in self:
            current_amount = wizard.amount
            wizard.amount = current_amount - wizard.global_tax_amount
            
            if wizard.global_tax_amount > 0:
                wizard.payment_difference_handling = 'reconcile'
            
        return res

    @api.depends('amount', 'payment_difference_handling')
    def _compute_payment_difference(self):
        res = super(inheritAccountPaymentRegister,self)._compute_payment_difference()
        for wizard in self:
            wizard.total_difference = wizard.payment_difference
            wizard.payment_difference = wizard.total_difference - wizard.global_tax_amount
        return res


    def _create_payment_vals_from_wizard(self):
        res = super(inheritAccountPaymentRegister,self)._create_payment_vals_from_wizard()

        if not 'write_off_line_vals' in res:
            res['write_off_line_vals'] = {
            
            }

        res['write_off_line_vals']['global_tax'] = []
        if self.payment_difference_handling != 'open':
            for tax in self.global_tax :
                res['write_off_line_vals']['global_tax'].append({
                    'name': tax.global_tax_id.name,
                    'amount': tax.amount,
                    'account_id': tax.global_tax_id.akun.id,
                    'currency_id': tax.currency_id.id,
                })

        return res

    @api.depends('payment_difference_handling')
    def _compute_payment_difference_handling(self):
        for wizard in self:
            taxAmount = 0

            if wizard.payment_difference_handling != 'open':
                for line in wizard.global_tax:
                    taxAmount += line.amount
            
            wizard.global_tax_amount = taxAmount