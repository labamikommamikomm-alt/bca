# my_borrow_module/wizards/create_borrow_po_line_wizard.py
from odoo import models, fields, api, _

class CreateBorrowPOLineWizard(models.TransientModel):
    _name = 'create.borrow.po.line.wizard'
    _description = 'Baris Wizard Peminjaman (Purchase Order)'

    wizard_id = fields.Many2one('create.borrow.po.wizard', string='Wizard Referensi', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Produk', required=True, domain=[('purchase_ok', '=', True)])
    quantity = fields.Float(string='Kuantitas', default=1.0, required=True)
    uom_id = fields.Many2one('uom.uom', string='Satuan Ukur', required=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_po_id.id or self.product_id.uom_id.id
            if self.product_id.description_purchase:
                self.name = self.product_id.description_purchase
            else:
                self.name = self.product_id.name
        else:
            self.uom_id = False
            self.name = False

    name = fields.Char(string='Deskripsi Produk', compute='_compute_name', store=True)

    @api.depends('product_id')
    def _compute_name(self):
        for rec in self:
            rec.name = rec.product_id.name if rec.product_id else False