# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools.misc import get_lang
from odoo.exceptions import ValidationError, RedirectWarning, UserError

class PurchaseOrderInherit(models.Model):
    _inherit = 'purchase.order'

    prepaid = fields.Boolean(string='Dibayar Dimuka')
    
    
    prepaid_bill = fields.Many2one('account.move', 
        domain="[('journal_id.type', '=', 'purchase'), ('used_bill', '=', False), ('partner_id', '=', partner_id)]",)
    
        
    def _bill_confirmation(self):
        # get procurement group
        group = self.env['procurement.group'].search([('name', '=', self.name)])
        group = group[0]
        # get stock picking
        stock_pickings = self.env['stock.picking'].search([
            ('group_id', '=', group.id),
            ('state', '=', 'assigned'),
        ])
        
        # raise UserError(str(len(stock_pickings)))
        
        # Validate stock
        pickings_to_do = self.env['stock.picking']
        for picking in stock_pickings:
            pickings_to_do |= picking
            # self.env['stock.immediate.transfer'].with_context(
            #     {
            #         'active_model': 'stock.picking',
            #         'active_ids': picking.id,
            #         'default_pick_ids': [picking.id]
            #     }
            # ).process()
        for picking in pickings_to_do:
            if picking.state == 'draft':
                picking.action_confirm()
                if picking.state != 'assigned':
                    picking.action_assign()
                    if picking.state != 'assigned':
                        raise UserError(_("Could not reserve all requested products. Please use the \'Mark as Todo\' button to handle the reservation manually."))
            for move in picking.move_lines.filtered(lambda m: m.state not in ['done', 'cancel']):
                for move_line in move.move_line_ids:
                    move_line.qty_done = move_line.product_uom_qty
                    
        pickings_to_do.with_context(skip_immediate=True).button_validate()
        
        # Create bill
        res=self.action_create_invoice()
        
        vendor_bill = self.env['account.move'].search([('id','=',res['res_id'])])
        vendor_bill = vendor_bill[0]
        
        vendor_bill.invoice_date = fields.Date.today()
        vendor_bill.action_post()
        
        if (self.prepaid_bill.amount_total < vendor_bill.amount_total):
            # Pay bill
            self.env['account.payment.register'].with_context(
                {'active_model': 'account.move',
                'active_ids': vendor_bill.id}
            ).create({
                'journal_id': 10,
                'payment_type': 'outbound',
                'payment_method_id': 2,
                'amount': self.prepaid_bill.amount_total,
                'payment_difference_handling': 'open'
            }).action_create_payments()
        else:
            # Pay bill
            self.env['account.payment.register'].with_context(
                {'active_model': 'account.move',
                'active_ids': vendor_bill.id}
            ).create({
                'journal_id': 10,
                'payment_type': 'outbound',
                'payment_method_id': 2
            }).action_create_payments()
        
        self.prepaid_bill.used_bill = True
        
    def button_confirm(self):
        res = super(PurchaseOrderInherit, self).button_confirm()
        
        if (self.prepaid):
            self._bill_confirmation()
        return res
        
class PurchaseOrderLineInherit(models.Model):
    _inherit = 'purchase.order.line'
    
    product_uom_category_id = fields.Many2one('uom.category')
    
    def _product_id_change(self):
        if not self.product_id:
            return

        if self.product_id.multi_uom_enabled:
            self.product_uom_category_id = self.product_id.multi_uom_category_id
        else:
            self.product_uom_category_id = self.product_id.uom_id.category_id
            self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        product_lang = self.product_id.with_context(
            lang=get_lang(self.env, self.partner_id.lang).code,
            partner_id=self.partner_id.id,
            company_id=self.company_id.id,
        )
        self.name = self._get_product_purchase_description(product_lang)

        self._compute_tax_id()