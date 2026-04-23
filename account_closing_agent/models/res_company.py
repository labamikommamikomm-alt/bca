# -*- coding: utf-8 -*-
from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    retained_earnings_account_id = fields.Many2one(
        'account.account', 
        string='Retained Earnings Account',
        help='Account used to transfer net profit/loss at the end of the fiscal year.'
    )
    closing_journal_id = fields.Many2one(
        'account.journal', 
        string='Closing Journal',
        domain="[('type', '=', 'general')]",
        help='Journal used for year-end closing entries.'
    )
