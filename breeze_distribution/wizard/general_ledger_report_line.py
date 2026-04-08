from odoo import models, fields, api

class GeneralLedgerReportLine(models.TransientModel):
    _name = 'general.ledger.report.line'
    _description = 'Baris Laporan Buku Besar'

    wizard_id = fields.Many2one('general.ledger.wizard', string="Wizard")
    account_id = fields.Many2one('account.account', string='Nomor Akun')
    date = fields.Date(string='Tanggal')
    journal_id = fields.Many2one('account.journal', string='Jurnal')
    ref = fields.Char(string='Referensi')
    name = fields.Char(string='Keterangan')
    debit = fields.Float(string='Debit')
    credit = fields.Float(string='Kredit')
    cumulated_balance = fields.Float(string='Saldo Terkumpul')

    # Ensure it's ordered properly in the view
    _order = 'account_id asc, date asc, id asc'
