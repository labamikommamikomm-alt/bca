# l10n_id_coretax/models/account_move.py
from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    # Field di header invoice (tab utama)
    jenis_faktur = fields.Selection([('Normal', 'Normal')], string='Jenis Faktur', default='Normal', readonly=True, states={'draft': [('readonly', False)]})
    kode_transaksi = fields.Selection(related='partner_id.kode_transaksi', string='Kode Transaksi', readonly=True)
    keterangan_tambahan_faktur = fields.Char(string='Keterangan Tambahan (Faktur)', readonly=True, states={'draft': [('readonly', False)]})
    cap_fasilitas = fields.Char(string='Cap Fasilitas', readonly=True, states={'draft': [('readonly', False)]})
    
    # Field untuk sheet Keterangan
    keterangan_coretax = fields.Text(string='Keterangan Coretax', help="Isi keterangan ini akan diekspor ke sheet 'Keterangan'.")
    
    # Field untuk sheet REF (One2many)
    dokumen_referensi_ids = fields.One2many('account.move.dokumen.referensi', 'move_id', string='Dokumen Referensi')
    partner_is_pkp = fields.Boolean(
        string="Partner adalah PKP",
        compute='_compute_partner_is_pkp',
        store=True  # Tetap store=True agar performa baik
    )

    @api.depends('partner_id')
    def _compute_partner_is_pkp(self):
        for move in self:
            # Cek apakah partner punya field l10n_id_pkp untuk keamanan
            if hasattr(move.partner_id, 'l10n_id_pkp'):
                move.partner_is_pkp = move.partner_id.l10n_id_pkp
            else:
                move.partner_is_pkp = False
    
class AccountMoveDokumenReferensi(models.Model):
    _name = 'account.move.dokumen.referensi'
    _description = 'Dokumen Referensi untuk Coretax'
    
    move_id = fields.Many2one('account.move', string='Invoice', required=True, ondelete='cascade')
    jenis_dokumen = fields.Char(string='Jenis Dokumen')
    nomor_dokumen = fields.Char(string='Nomor Dokumen')
    tanggal_dokumen = fields.Date(string='Tanggal Dokumen')

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def get_total_diskon(self):
        """Menghitung nilai absolut diskon dari persentase."""
        self.ensure_one()
        return (self.price_unit * self.quantity) * (self.discount / 100)