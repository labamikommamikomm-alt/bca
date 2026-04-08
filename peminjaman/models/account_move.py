from odoo import models, fields, api, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    is_peminjaman = fields.Boolean(string="Peminjaman Barang", default=False,
        help="Menandakan invoice/bill ini terkait dengan peminjaman barang.")
    is_pengembalian = fields.Boolean(string="Pengembalian Barang", default=False,
        help="Menandakan invoice/bill ini terkait dengan pengembalian barang.")

    @api.onchange('is_peminjaman', 'is_pengembalian')
    def _onchange_borrow_return_flags_move(self):
        # The base _recompute_dynamic_lines will re-evaluate price_unit and taxes for lines
        # when the flags are changed on the header.
        # We need to explicitly set price_unit and clear taxes on lines first
        if self.is_peminjaman or self.is_pengembalian:
            for line in self.invoice_line_ids:
                line.price_unit = 0.0
                line.tax_ids = [(5, 0, 0)] # Remove all taxes by linking to nothing
            # The next calls will correctly recompute totals based on the 0 prices
            self._recompute_dynamic_lines(recompute_all_taxes=True)
            self._recompute_tax_lines()


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_peminjaman') or vals.get('is_pengembalian'):
                if 'invoice_line_ids' in vals:
                    new_lines = []
                    for line_cmd in vals['invoice_line_ids']:
                        if line_cmd[0] == 0: # Create command for new line
                            line_vals = line_cmd[2]
                            line_vals['price_unit'] = 0.0
                            line_vals['tax_ids'] = [(5, 0, 0)] # Clear taxes
                            new_lines.append(line_cmd)
                        else:
                            new_lines.append(line_cmd) # Keep other commands (e.g., update existing lines) as is
                    vals['invoice_line_ids'] = new_lines
        return super().create(vals_list)


    def write(self, vals):
        res = super().write(vals) # Call super.write first
        # Handle cases where flags are changed after creation
        # After super().write, self.invoice_line_ids will be up-to-date
        if 'is_peminjaman' in vals and vals['is_peminjaman']:
            for line in self.invoice_line_ids:
                line.price_unit = 0.0
                line.tax_ids = [(5, 0, 0)]
            self._recompute_dynamic_lines(recompute_all_taxes=True)
            self._recompute_tax_lines()
        elif 'is_pengembalian' in vals and vals['is_pengembalian']:
            for line in self.invoice_line_ids:
                line.price_unit = 0.0
                line.tax_ids = [(5, 0, 0)]
            self._recompute_dynamic_lines(recompute_all_taxes=True)
            self._recompute_tax_lines()
        
        return res

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_peminjaman_line = fields.Boolean(related='move_id.is_peminjaman', store=True, readonly=False)
    is_pengembalian_line = fields.Boolean(related='move_id.is_pengembalian', store=True, readonly=False)

    @api.onchange('is_peminjaman_line', 'is_pengembalian_line')
    def _onchange_peminjaman_pengembalian_flag_line(self):
        # This onchange will trigger for each line individually when the related field changes
        # (e.g., when the flag on the move header is toggled).
        if self.is_peminjaman_line or self.is_pengembalian_line:
            self.price_unit = 0.0
            self.tax_ids = [(5, 0, 0)] # Remove taxes

    # Override _onchange_price_subtotal to ensure price_unit stays 0 for these types
    # This method is designed to be called on a recordset, so we iterate.
    @api.onchange('quantity', 'discount', 'price_unit', 'tax_ids')
    def _onchange_price_subtotal(self):
        # Iterate over each record in the current recordset (self)
        for line in self:
            if line.is_peminjaman_line or line.is_pengembalian_line:
                # If the flags are set, force price_unit to 0 and recalculate
                if line.price_unit != 0.0:
                    line.price_unit = 0.0
                    line.tax_ids = [(5, 0, 0)] # Clear taxes
                    # After forcing price_unit to 0, call the super method for this specific line
                    # to let Odoo's core logic recompute the subtotal and other related values.
                    # We pass 'self=line' to ensure the super method operates on a singleton.
                    super(AccountMoveLine, line)._onchange_price_subtotal()
                else:
                    # If price_unit is already 0, just call the super method
                    super(AccountMoveLine, line)._onchange_price_subtotal()
            else:
                # If it's not a borrow/return line, just call the super method as normal
                super(AccountMoveLine, line)._onchange_price_subtotal()