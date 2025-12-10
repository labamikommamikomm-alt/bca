from odoo import models, fields, api

class GlobalTax(models.Model):
    _name='breeze_distribution.global_tax'
    _rec_name = 'name'
    
    name = fields.Char(string='Name', required=True)
    jumlah = fields.Float(string='Jumlah Pajak (%)', required=True)
    akun = fields.Many2one('account.account', string='Akun Pajak', required=True)
    active = fields.Boolean(string='Aktif', default=False)
    state = fields.Char(string='Status', compute='get_state')
    berlaku_jika = fields.Boolean(string='Berlaku Jika')
    kondisi = fields.Selection([
        ('lebih', 'Lebih dari'),
        ('lebih_sama', 'Lebih dari / Sama dengan'),
        ('kurang', 'Kurang dari'),
        ('kurang_sama', 'Kurang dari / Sama dengan')
    ])
    nilai = fields.Float(string='Nilai')
    
    
    def get_state(self):
        for record in self:
            if record.active:
                record.state = 'Aktif'
            else:
                record.state = 'Tidak Aktif'