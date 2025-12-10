# l10n_id_coretax/models/res_partner.py
from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    nama_npwp = fields.Char(string='Nama NPWP')
    alamat_npwp = fields.Text(string='Alamat NPWP')
    kode_transaksi = fields.Selection([
        ('01', '01 - kepada selain Pemungut PPN'),
        ('02', '02 - kepada Pemungut PPN Instansi Pemerintah'),
        ('03', '03 - kepada Pemungut PPN selain Instansi Pemerintah'),
        ('04', '04 - DPP Nilai Lain'),
        ('05', '05 - Besaran tertentu'),
        ('06', '06 - kepada orang pribadi pemegang paspor luar negeri (16E UU PPN)'),
        ('07', '07 - penyerahan dengan fasilitas PPN atau PPN dan PPnBM tidak dipungut/ditanggung pemerintah'),
        ('08', '08 - penyerahan dengan fasilitas dibebaskan PPN atau PPN dan PPnBM'),
        ('09', '09 - penyerahan aktiva yang menurut tujuan semula tidak diperjualbelikan (16D UU PPN)'),
        ('10', '10 - Penyerahan lainnya'),
    ], string='Default Kode Transaksi', default='01')