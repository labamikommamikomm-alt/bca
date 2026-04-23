# -*- coding: utf-8 -*-
from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    retained_earnings_account_id = fields.Many2one(
        related='company_id.retained_earnings_account_id',
        string='Retained Earnings Account',
        readonly=False
    )
    closing_journal_id = fields.Many2one(
        related='company_id.closing_journal_id',
        string='Closing Journal',
        readonly=False
    )
