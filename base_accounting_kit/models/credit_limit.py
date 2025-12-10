# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2019-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.translate import _
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    warning_stage = fields.Float(string='Warning Amount',
                                 help="A warning message will appear once the "
                                      "selected customer is crossed warning "
                                      "amount. Set its value to 0.00 to"
                                      " disable this feature")
    blocking_stage = fields.Float(string='Blocking Amount',
                                  help="Cannot make sales once the selected "
                                       "customer is crossed blocking amount."
                                       "Set its value to 0.00 to disable "
                                       "this feature")
    due_amount = fields.Float(string="Total Sale",
                              compute="compute_due_amount")
    active_limit = fields.Boolean("Active Credit Limit", default=False)

    enable_credit_limit = fields.Boolean(string="Credit Limit Enabled",
                                         compute="_compute_enable_credit_limit")

    def compute_due_amount(self):
        for rec in self:
            if not rec.id:
                continue
            rec.due_amount = rec.credit - rec.debit

    def _compute_enable_credit_limit(self):
        """ Check credit limit is enabled in account settings """
        params = self.env['ir.config_parameter'].sudo()
        customer_credit_limit = params.get_param('customer_credit_limit',
                                                 default=False)
        for rec in self:
            rec.enable_credit_limit = True if customer_credit_limit else False

    @api.constrains('warning_stage', 'blocking_stage')
    def constrains_warning_stage(self):
        if self.active_limit and self.enable_credit_limit:
            if self.warning_stage >= self.blocking_stage:
                if self.blocking_stage > 0:
                    raise UserError(_(
                        "Warning amount should be less than Blocking amount"))


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    has_due = fields.Boolean()
    is_warning = fields.Boolean()
    due_amount = fields.Float(related='partner_id.due_amount')

    def _action_confirm(self):
        """To check the selected customers due amount is exceed than
        blocking stage"""
        if self.partner_id.active_limit \
                and self.partner_id.enable_credit_limit:
            if self.due_amount >= self.partner_id.blocking_stage:
                if self.partner_id.blocking_stage != 0:
                    raise UserError(_(
                        "%s is in  Blocking Stage and "
                        "has a due amount of %s %s to pay") % (
                                        self.partner_id.name, self.due_amount,
                                        self.currency_id.symbol))
        return super(SaleOrder, self)._action_confirm()

    @api.onchange('partner_id')
    def check_due(self):
        """To show the due amount and warning stage"""
        if self.partner_id and self.partner_id.due_amount > 0 \
                and self.partner_id.active_limit \
                and self.partner_id.enable_credit_limit:
            self.has_due = True
        else:
            self.has_due = False
        if self.partner_id and self.partner_id.active_limit\
                and self.partner_id.enable_credit_limit:
            if self.due_amount >= self.partner_id.warning_stage:
                if self.partner_id.warning_stage != 0:
                    self.is_warning = True
        else:
            self.is_warning = False
    
    
    def _create_invoices(self, grouped=False, final=False, date=None):
        _logger.info("---------- START _create_invoices OVERRIDE (Explicit Discount Line - Final Attempt) ----------")

        invoices = super(SaleOrder, self)._create_invoices(grouped, final, date)
        _logger.info(f"Super call completed. Created {len(invoices)} invoices.")

        for invoice in invoices:
            _logger.info(f"Processing Invoice ID: {invoice.id}, Name: {invoice.name}, Type: {invoice.move_type}")
            if invoice.move_type == 'out_invoice':
                if invoice.state != 'draft':
                    _logger.warning(f"Invoice {invoice.name} is not in draft state. Skipping line modification.")
                    continue

                lines_to_update_vals = []
                lines_to_add_vals = []

                current_invoice_lines_copy = list(invoice.invoice_line_ids)

                for inv_line in current_invoice_lines_copy:
                    sale_line = inv_line.sale_line_ids[:1]

                    if sale_line and sale_line.discount:
                        _logger.info(f"--- Handling Sale Line ID: {sale_line.id} (Product: {sale_line.product_id.name}) ---")

                        original_gross_price_unit = sale_line.price_unit
                        discount_percentage = sale_line.discount
                        
                        calculated_discount_amount = original_gross_price_unit * inv_line.quantity * (discount_percentage / 100.0)

                        if calculated_discount_amount > 0:
                            _logger.info(f"  Original Gross Price Unit (from SO line): {original_gross_price_unit}")
                            _logger.info(f"  Calculated Discount Amount: {calculated_discount_amount}")
                            _logger.info(f"  Existing Invoice Line ID {inv_line.id} (Current Price Unit: {inv_line.price_unit}, Current Discount: {inv_line.discount}%)")

                            # --- LANGKAH 1: Kumpulkan data untuk MODIFIKASI BARIS PRODUK YANG SUDAH ADA ---
                            lines_to_update_vals.append({
                                'id': inv_line.id,
                                'price_unit': original_gross_price_unit,
                                'discount': 0.0,
                                'name': _("%s (Harga Bruto)") % inv_line.name,
                            })
                            _logger.info(f"  Prepared update for existing Invoice Line ID {inv_line.id}: New Price Unit: {original_gross_price_unit}, New Discount: 0.0%")
                            
                            # --- LANGKAH 2: Kumpulkan data untuk TAMBAHKAN BARIS DISKON TERPISAH ---
                            sales_discount_account = self.env['account.account'].search([
                                ('name', 'ilike', 'Sales Discount'),
                                ('company_id', '=', invoice.company_id.id)
                            ], limit=1)

                            if not sales_discount_account:
                                sales_discount_account = self.env['account.account'].search([
                                    ('code', '=', '42000070'),
                                    ('company_id', '=', invoice.company_id.id)
                                ], limit=1)

                            if not sales_discount_account:
                                _logger.error(f"Sales Discount Account not found for company {invoice.company_id.name}. Please configure it.")
                                raise UserError(_(
                                    "Akun 'Sales Discount' tidak ditemukan di perusahaan Anda (%s). "
                                    "Harap konfigurasikan akun ini di Bagan Akun Anda. "
                                    "Disarankan untuk menggunakan tipe akun 'Beban' (Expense) "
                                    "atau 'Pendapatan Lain' (Other Income) yang berfungsi sebagai kontra-pendapatan."
                                ) % invoice.company_id.name)

                            _logger.info(f"  Found Sales Discount Account: {sales_discount_account.code} ({sales_discount_account.name}), Type: {sales_discount_account.user_type_id.name}")

                            discount_tax_ids = sale_line.tax_id.ids if sale_line.tax_id else []
                            _logger.info(f"  Applying tax_ids {discount_tax_ids} to discount line.")

                            discount_line_vals = {
                                'name': _("Diskon Penjualan untuk %s (%.2f%%)") % (sale_line.product_id.name, discount_percentage),
                                'product_id': sale_line.product_id.id,
                                'quantity': 1,
                                'price_unit': -calculated_discount_amount,
                                'account_id': sales_discount_account.id,
                                'tax_ids': [(6, 0, discount_tax_ids)],
                                'exclude_from_invoice_tab': False,
                                'sale_line_ids': [(6, 0, [])],
                            }
                            lines_to_add_vals.append((0, 0, discount_line_vals))
                            _logger.info(f"  Prepared new Discount Line: {discount_line_vals}")

                # --- LAKUKAN SEMUA PERUBAHAN DALAM SATU OPERASI WRITE PADA INVOICE ---
                if lines_to_update_vals or lines_to_add_vals:
                    update_commands = []
                    for vals in lines_to_update_vals:
                        line_id = vals.pop('id')
                        update_commands.append((1, line_id, vals))
                    
                    update_commands.extend(lines_to_add_vals)

                    _logger.info(f"Executing batch update/add for Invoice ID: {invoice.id} with {len(update_commands)} commands.")
                    invoice.write({'invoice_line_ids': update_commands})
                            
                _logger.info("Triggering invoice total recomputation...")
                # Ini adalah metode yang akan memicu perhitungan ulang amount_untaxed, amount_tax, amount_total
                invoice._onchange_invoice_line_ids()
                
                # HAPUS BARIS INI: invoice._recompute_debit_credit_from_amount()
                # HAPUS BARIS INI: _logger.info(f"  Recomputed debit/credit for Invoice ID: {invoice.id}")

                _logger.info("--- Final Invoice Lines after override ---")
                # Untuk logging final_debit dan final_credit, akses langsung line_ids dari invoice
                # Pastikan data terupdate dengan memuat ulang invoice jika perlu (tidak selalu diperlukan setelah write)
                invoice.invalidate_cache(['invoice_line_ids']) # Untuk memastikan data terbaru di cache
                invoice.refresh() # Untuk memastikan data terbaru dari DB

                for final_inv_line in invoice.invoice_line_ids:
                    _logger.info(f"  Line ID: {final_inv_line.id}, Name: {final_inv_line.name}, Product: {final_inv_line.product_id.name}, "
                                 f"Price Unit: {final_inv_line.price_unit}, Qty: {final_inv_line.quantity}, "
                                 f"Disc: {final_inv_line.discount}%, Subtotal: {final_inv_line.price_subtotal}, "
                                 f"Debit (auto): {final_inv_line.debit}, Credit (auto): {final_inv_line.credit}, "
                                 f"Account: {final_inv_line.account_id.code} ({final_inv_line.account_id.name}), "
                                 f"Account Type: {final_inv_line.account_id.user_type_id.name}, "
                                 f"Tax IDs: {final_inv_line.tax_ids.ids}, "
                                 f"Sale Lines: {final_inv_line.sale_line_ids.ids}")
                
                _logger.info(f"  Invoice Total - Untaxed: {invoice.amount_untaxed}, Tax: {invoice.amount_tax}, Total: {invoice.amount_total}")
                
                # Final check for balance on the journal entry itself
                # HAPUS BARIS INI: invoice._recompute_debit_credit_from_amount()
                # Akses line_ids langsung dari invoice untuk pengecekan saldo
                final_move_debit = sum(line.debit for line in invoice.line_ids)
                final_move_credit = sum(line.credit for line in invoice.line_ids)

                _logger.info(f"  Journal Entry (Invoice ID: {invoice.id}) - Total Debit: {final_move_debit}, Total Credit: {final_move_credit}, Difference: {final_move_debit - final_move_credit}")
                
                if abs(final_move_debit - final_move_credit) > 0.001:
                    _logger.error(f"  UNBALANCED JOURNAL ENTRY DETECTED for Invoice ID: {invoice.id}!")
                    raise UserError(_("Jurnal entry untuk invoice %s tidak seimbang setelah modifikasi. Selisih: %.2f") % (invoice.name, final_move_debit - final_move_credit))
                else:
                    _logger.info(f"  Journal Entry for Invoice ID: {invoice.id} is BALANCED.")

                _logger.info("---------- END _create_invoices OVERRIDE ----------")

        return invoices




class AccountMove(models.Model):
    _inherit = 'account.move'

    has_due = fields.Boolean()
    is_warning = fields.Boolean()
    due_amount = fields.Float(related='partner_id.due_amount')

    def action_post(self):
        """To check the selected customers due amount is exceed than
        blocking stage"""
        pay_type = ['out_invoice', 'out_refund', 'out_receipt']
        for rec in self:
            if rec.partner_id.active_limit and rec.move_type in pay_type \
                    and rec.partner_id.enable_credit_limit:
                if rec.due_amount >= rec.partner_id.blocking_stage:
                    if rec.partner_id.blocking_stage != 0:
                        raise UserError(_(
                            "%s is in  Blocking Stage and "
                            "has a due amount of %s %s to pay") % (
                                            rec.partner_id.name, rec.due_amount,
                                            rec.currency_id.symbol))
        return super(AccountMove, self).action_post()

    @api.onchange('partner_id')
    def check_due(self):
        """To show the due amount and warning stage"""
        if self.partner_id and self.partner_id.due_amount > 0 \
                and self.partner_id.active_limit \
                and self.partner_id.enable_credit_limit:
            self.has_due = True
        else:
            self.has_due = False
        if self.partner_id and self.partner_id.active_limit \
                and self.partner_id.enable_credit_limit:
            if self.due_amount >= self.partner_id.warning_stage:
                if self.partner_id.warning_stage != 0:
                    self.is_warning = True
        else:
            self.is_warning = False
