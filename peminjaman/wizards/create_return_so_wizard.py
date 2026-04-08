# my_borrow_module/wizards/create_return_so_wizard.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CreateReturnSOWizard(models.TransientModel):
    _name = 'create.return.so.wizard'
    _description = 'Wizard untuk Membuat Pengembalian (Sales Order)'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    date_order = fields.Datetime(string='Tanggal SO', required=True, default=fields.Datetime.now())
    # Ganti many2many product_ids menjadi one2many ke model baris wizard baru
    return_line_ids = fields.One2many('create.return.so.line.wizard', 'wizard_id', string='Produk yang Dikembalikan')

    def action_create_return_so(self):
        self.ensure_one()
        if not self.return_line_ids:
            raise UserError(_("Anda harus menambahkan setidaknya satu produk yang akan dikembalikan."))

        order_lines = []
        for line in self.return_line_ids:
            if not line.product_id or line.quantity <= 0:
                raise UserError(_("Produk dan kuantitas harus valid untuk setiap baris."))
            order_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.uom_id.id, # Gunakan UoM dari baris wizard
                'price_unit': 0.0, # Force to 0
                'name': line.product_id.name,
            }))

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'date_order': self.date_order,
            'is_pengembalian': True, # Set the flag
            'order_line': order_lines,
        })

        # Return an action to open the newly created Sales Order
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pengembalian (Sales Order)'),
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
        }