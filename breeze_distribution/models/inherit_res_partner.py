import json
from locale import currency
from odoo import models, fields, api, exceptions
from odoo.tools.misc import get_lang
from dateutil.relativedelta import relativedelta



class InheritResPartner(models.Model):
    _inherit = 'res.partner'

    type_customer = fields.Selection([
        ('rumah_sakit', 'Rumah Sakit'),
        ('apotek', 'Apotek'),
        ('dinas', 'Dinas'),
        ('lainnya', 'Lainnya')
    ], string="Type Customer")


    nama_npwp = fields.Char(string="Nama NPWP")
    jalan_npwp = fields.Char(string="Jalan NPWP")
    kota_npwp = fields.Char(string="Kota")
    provinsi_npwp_id = fields.Many2one('res.country.state', string="Provinsi")
    kode_pos_npwp = fields.Char(string="Kode Pos")
    negara_npwp_id = fields.Many2one('res.country', string="Negara")
    alamat_npwp = fields.Char(string="Alamat NPWP", compute='_get_alamat_npwp')
    
    nik = fields.Char(string="NIK")
    nama_ktp = fields.Char(string="Nama KTP")
    jalan_ktp = fields.Char(string="Jalan KTP")
    kota_ktp = fields.Char(string="Kota")
    provinsi_ktp_id = fields.Many2one('res.country.state', string="Provinsi")
    kode_pos_ktp = fields.Char(string="Kode Pos")
    negara_ktp_id = fields.Many2one('res.country', string="Negara")
    alamat_ktp = fields.Char(string="Alamat KTP", compute='_get_alamat_ktp')
    
    def _get_alamat_npwp(self):
        for record in self:
            record.alamat_npwp = ((record.jalan_npwp if record.jalan_npwp != False else '') 
            +' '+ (record.kota_npwp if record.kota_npwp != False else '')
            +' '+ (record.provinsi_npwp_id.name if record.provinsi_npwp_id.name != False else '')
            +' '+ (record.kode_pos_npwp if record.kode_pos_npwp != False else '')).upper()
    
    def _get_alamat_ktp(self):
        for record in self:
            record.alamat_ktp = ((record.jalan_ktp if record.jalan_ktp != False else '') 
            +' '+ (record.kota_ktp if record.kota_ktp != False else '')
            +' '+ (record.provinsi_ktp_id.name if record.provinsi_ktp_id.name != False else '')
            +' '+ (record.kode_pos_ktp if record.kode_pos_ktp != False else '')).upper()
            
    
    
