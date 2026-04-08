# my_borrow_module/wizards/create_return_so_line_wizard.py
from odoo import models, fields, api, _

class CreateReturnSOLineWizard(models.TransientModel):
    _name = 'create.return.so.line.wizard'
    _description = 'Baris Wizard Pengembalian (Sales Order)'

    wizard_id = fields.Many2one('create.return.so.wizard', string='Wizard Referensi', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Produk', required=True, domain=[('sale_ok', '=', True)])
    quantity = fields.Float(string='Kuantitas', default=1.0, required=True)
    uom_id = fields.Many2one('uom.uom', string='Satuan Ukur', required=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id # Default UoM for sales
            if self.product_id.description_sale:
                self.name = self.product_id.description_sale
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