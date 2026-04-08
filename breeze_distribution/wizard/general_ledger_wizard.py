from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
import datetime

class GeneralLedgerWizard(models.TransientModel):
    _name = 'general.ledger.wizard'
    _description = 'Wizard untuk Laporan Buku Besar'

    # ... (Field definition tetap sama) ...
    date_from = fields.Date(string='Dari Tanggal', required=True, default=fields.Date.today().replace(day=1))
    date_to = fields.Date(string='Sampai Tanggal', required=True, default=fields.Date.today())
    account_ids = fields.Many2many(
        'account.account',
        string='Nomor Akun',
        required=True
    )
    journal_ids = fields.Many2many(
        'account.journal',
        string='Journal',
    )
    report_file = fields.Binary('Report File')
    file_name = fields.Char('File Name')

    # FUNGSI _get_initial_balance
    def _get_initial_balance(self, accounts, date_from):
        """Hitung saldo sebelum date_from (Semua transaksi < date_from)"""
        initial_balances = {}
        for account in accounts:
            self.env.cr.execute("""
                SELECT COALESCE(SUM(debit - credit), 0)
                FROM account_move_line
                WHERE account_id = %s AND date < %s AND parent_state = 'posted'
            """, (account.id, date_from))
            balance = self.env.cr.fetchone()[0] or 0.0
            initial_balances[account.id] = balance
        return initial_balances

    # ... (FUNGSI _get_base_domain dan generate_report tetap sama) ...
    def _get_base_domain(self, date_field='date'):
        # ... (kode ini tetap sama) ...
        domain = [
            ('move_id.state', '=', 'posted')
        ]
        
        if self.date_from:
            domain.append((date_field, '>=', self.date_from))
        if self.date_to:
            domain.append((date_field, '<=', self.date_to))
        
        account_filter = ('account_id', 'in', self.account_ids.ids)
        
        if self.journal_ids:
            journal_filter = ('journal_id', 'in', self.journal_ids.ids)
            domain += ['|', account_filter, journal_filter]
        else:
            domain.append(account_filter)
            
        return domain

    def generate_report(self):
        """Buat baris-baris laporan di general.ledger.report.line termasuk Saldo Awal, lalu tampilkan"""
        self.ensure_one()

        # 1. Tentukan domain filter untuk transaksi 
        base_domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('move_id.state', '=', 'posted')
        ]
        
        # 2. Ambil data
        lines = self.env['account.move.line'].search(base_domain, order='date asc, id asc')

        # 3. Ambil Saldo Awal
        accounts = self.account_ids
        initial_balances = self._get_initial_balance(accounts, self.date_from)

        # 4. Hapus data laporan lama dari user ini saja agar tidak menumpuk
        self.env['general.ledger.report.line'].search([('wizard_id', '=', self.id)]).unlink()

        report_lines = []
        
        for account in accounts:
            current_balance = initial_balances.get(account.id, 0.0)
            
            # --- SALDO AWAL ---
            report_lines.append({
                'wizard_id': self.id,
                'account_id': account.id,
                'date': self.date_from,
                'name': 'Saldo awal',
                'debit': 0.0,
                'credit': 0.0,
                'cumulated_balance': current_balance,
            })
            
            # --- TRANSAKSI BERJALAN ---
            account_lines = lines.filtered(lambda l: 
                l.account_id.id == account.id and 
                (not self.journal_ids or l.journal_id.id in self.journal_ids.ids)
            )
            
            for line in account_lines:
                current_balance += line.debit - line.credit
                
                desc = line.name or ''
                if line.ref and line.ref != desc:
                    desc = f"{line.ref} - {desc}" if desc else line.ref
                    
                report_lines.append({
                    'wizard_id': self.id,
                    'account_id': account.id,
                    'date': line.date,
                    'journal_id': line.journal_id.id,
                    'ref': line.ref,
                    'name': desc,
                    'debit': line.debit,
                    'credit': line.credit,
                    'cumulated_balance': current_balance,
                })

        # Insert semua baris
        if report_lines:
            self.env['general.ledger.report.line'].create(report_lines)

        # Tampilkan
        action = {
            'name': 'Laporan Buku Besar',
            'type': 'ir.actions.act_window',
            'res_model': 'general.ledger.report.line',
            'view_mode': 'tree',
            'views': [(self.env.ref('breeze_distribution.view_general_ledger_report_line_tree').id, 'tree')],
            'search_view_id': self.env.ref('breeze_distribution.view_general_ledger_report_line_search').id,
            'domain': [('wizard_id', '=', self.id)],
            'context': {'search_default_group_by_account': 1, 'group_by': 'account_id'},
        }
        return action
    
    def export_report(self):
        """Fungsi BARU untuk Export Laporan ke Excel mengikuti format kertas (termasuk Saldo Awal)."""
        self.ensure_one()
        
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_('Library "xlsxwriter" is not installed. Please install it menggunakan: pip3 install xlsxwriter'))
            
        # 1. Tentukan domain filter untuk transaksi yang akan diexport
        base_domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('move_id.state', '=', 'posted')
        ]
        
        # 2. Ambil SEMUA data yang difilter dalam rentang tanggal
        lines = self.env['account.move.line'].search(base_domain, order='date asc, id asc')

        # 3. Ambil Saldo Awal
        accounts = self.account_ids
        initial_balances = self._get_initial_balance(accounts, self.date_from)
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Format Excel
        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
        subtitle_format = workbook.add_format({'font_size': 11, 'bold': True, 'align': 'center'})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        text_center = workbook.add_format({'align': 'center', 'border': 1})
        text_left = workbook.add_format({'align': 'left', 'border': 1})
        currency_format = workbook.add_format({'num_format': '#,##0', 'align': 'right', 'border': 1})
        
        for account in accounts:
            sheet_name = account.code[:31]  # Excel batasan nama sheet max 31 karakter
            sheet = workbook.add_worksheet(sheet_name)
            
            # --- Judul ---
            sheet.merge_range(0, 0, 0, 5, "BUKU BESAR", title_format)
            sheet.merge_range(1, 0, 1, 5, f"PERIODE: {self.date_from.strftime('%d %B %Y')} - {self.date_to.strftime('%d %B %Y')}".upper(), subtitle_format)
            
            # --- Header Akun ---
            sheet.write(3, 0, f"NAMA AKUN : {account.name}", subtitle_format)
            sheet.write(3, 4, f"KODE AKUN : {account.code}", subtitle_format)
            
            # Lebar Kolom
            sheet.set_column(0, 0, 5)   # NO
            sheet.set_column(1, 1, 12)  # TANGGAL
            sheet.set_column(2, 2, 40)  # KETERANGAN
            sheet.set_column(3, 3, 15)  # DEBIT
            sheet.set_column(4, 4, 15)  # KREDIT
            sheet.set_column(5, 5, 20)  # SALDO

            # --- Tabel Header ---
            headers = ["NO", "TANGGAL", "KETERANGAN", "DEBIT", "KREDIT", "SALDO"]
            for col_num, header in enumerate(headers):
                sheet.write(5, col_num, header, header_format)
            
            # --- SALDO AWAL ---
            row_num = 6
            saldo_awal = initial_balances.get(account.id, 0.0)
            current_balance = saldo_awal
            
            sheet.write(row_num, 0, "", text_center)
            sheet.write(row_num, 1, "", text_center)
            sheet.write(row_num, 2, "Saldo awal", text_left)
            sheet.write(row_num, 3, "-", currency_format)
            sheet.write(row_num, 4, "-", currency_format)
            sheet.write_number(row_num, 5, saldo_awal, currency_format)
            
            row_num += 1

            # --- Transaksi Berjalan ---
            account_lines = lines.filtered(lambda l: 
                l.account_id.id == account.id and 
                (not self.journal_ids or l.journal_id.id in self.journal_ids.ids)
            )

            index = 1
            for line in account_lines:
                current_balance += line.debit - line.credit
                
                desc = line.name or ''
                if line.ref and line.ref != desc:
                    desc = f"{line.ref} - {desc}" if desc else line.ref
                
                sheet.write(row_num, 0, index, text_center)
                sheet.write(row_num, 1, line.date.strftime('%d-%m-%y'), text_center)
                sheet.write(row_num, 2, desc, text_left)
                sheet.write_number(row_num, 3, line.debit, currency_format)
                sheet.write_number(row_num, 4, line.credit, currency_format)
                sheet.write_number(row_num, 5, current_balance, currency_format)
                
                row_num += 1
                index += 1

        workbook.close()
        output.seek(0)
        
        file_name = f"Laporan_Buku_Besar_{self.date_from}_to_{self.date_to}.xlsx"
        report_data = base64.b64encode(output.read())
        
        # Kita menggunakan ir.attachment agar file tersimpan sementara dan bisa diserve untuk download
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'datas': report_data,
            'type': 'binary',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }