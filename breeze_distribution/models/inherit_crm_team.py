from odoo import models, fields, api, exceptions


class inheritCrmTeam(models.Model):
    _inherit = "crm.team"


    invoice = fields.Many2many('account.move', string="Invoice", compute='inherit_invoice')

    def inherit_invoice(self):
        for record in self:
          assign = self.env['breeze_distribution.assign'].sudo().search([('sales_id.id', '=', self.id)])

          record.invoice = assign.invoice_id