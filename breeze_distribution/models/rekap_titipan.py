from odoo import models, fields, api

class RekapTitipan(models.Model):
    _name='breeze_distribution.rekap_titipan'
    _rec_name = 'tanggal'
    _order = 'tanggal desc'

    tanggal = fields.Date(string='Tanggal', default = lambda self: fields.Date.today())
    employee_id = fields.Many2one('hr.employee', string='Employee')
    invoice_id = fields.Many2one('account.move', string='Kode Tagihan')
    jumlah = fields.Float(string='Jumlah Bayar')
    metode = fields.Char(string='Metode Bayar')