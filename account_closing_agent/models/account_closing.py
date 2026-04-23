# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountYearEndClosing(models.Model):
    _name = 'account.year_end.closing'
    _description = 'Year-End Closing History'
    _order = 'year desc, create_date desc'

    year = fields.Integer(string='Year', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    move_id = fields.Many2one('account.move', string='Closing Journal Entry', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled')
    ], string='Status', compute='_compute_state', store=True)
    user_id = fields.Many2one('res.partner', string='Processed By', default=lambda self: self.env.user.partner_id)
    closing_date = fields.Date(string='Closing Date', default=fields.Date.today)

    @api.depends('move_id.state')
    def _compute_state(self):
        for rec in self:
            if not rec.move_id:
                rec.state = 'draft'
            elif rec.move_id.state == 'posted':
                rec.state = 'posted'
            elif rec.move_id.state == 'cancel':
                rec.state = 'cancelled'
            else:
                rec.state = 'draft'

    def action_view_move(self):
        self.ensure_one()
        return {
            'name': _('Closing Journal Entry'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'type': 'ir.actions.act_window',
        }

    def action_confirm(self):
        """ Post the move and update lock dates """
        self.ensure_one()
        if self.move_id and self.move_id.state == 'draft':
            self.move_id.action_post()
            # After posting, it's safe to lock
            date_to = self.move_id.date
            self.company_id.sudo().write({
                'fiscalyear_lock_date': date_to,
                'period_lock_date': date_to,
            })
        return True
