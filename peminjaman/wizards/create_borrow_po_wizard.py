# my_borrow_module/wizards/create_borrow_po_wizard.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CreateBorrowPOWizard(models.TransientModel):
    _name = 'create.borrow.po.wizard'
    _description = 'Wizard untuk Membuat Peminjaman (Purchase Order)'

    partner_id = fields.Many2one('res.partner', string='Vendor', required=True,)
    date_order = fields.Datetime(string='Tanggal PO', required=True, default=fields.Datetime.now())
    # Ganti many2many product_ids menjadi one2many ke model baris wizard baru
    borrow_line_ids = fields.One2many('create.borrow.po.line.wizard', 'wizard_id', string='Produk yang Dipinjam')

    def action_create_borrow_po(self):
        self.ensure_one()
        if not self.borrow_line_ids:
            raise UserError(_("Anda harus menambahkan setidaknya satu produk yang akan dipinjam."))

        order_lines = []
        for line in self.borrow_line_ids:
            if not line.product_id or line.quantity <= 0:
                raise UserError(_("Produk dan kuantitas harus valid untuk setiap baris."))
            order_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'product_qty': line.quantity,
                'product_uom': line.uom_id.id, # Gunakan UoM dari baris wizard
                'price_unit': 0.0, # Force to 0
                'name': line.product_id.name,
            }))

        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'date_order': self.date_order,
            'is_peminjaman': True, # Set the flag
            'order_line': order_lines,
        })

        # Return an action to open the newly created Purchase Order
        return {
            'type': 'ir.actions.act_window',
            'name': _('Peminjaman (Purchase Order)'),
            'res_model': 'purchase.order',
            'res_id': purchase_order.id,
            'view_mode': 'form',
            'target': 'current',
        }