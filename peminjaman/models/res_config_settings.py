from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    stock_interim_borrow_account_id = fields.Many2one(
        'account.account',
        string="Stock Interim Account for Borrow/Return (Zero Price)",
        config_parameter='my_borrow_module.stock_interim_borrow_account_id',
        help="Account to use for stock interim valuation when price is zero for borrow/return."
    )
    cogs_borrow_account_id = fields.Many2one(
        'account.account',
        string="COGS Account for Borrow/Return (Zero Price)",
        config_parameter='my_borrow_module.cogs_borrow_account_id',
        help="Account to use for Cost of Goods Sold when price is zero for borrow/return."
    )