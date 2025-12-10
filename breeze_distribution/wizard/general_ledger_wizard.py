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

    # FUNGSI _get_initial_balance KITA BIARKAN TAPI TIDAK DIPANGGIL DI EXPORT
    def _get_initial_balance(self):
        # ... (fungsi ini tetap ada, tapi tidak digunakan di export_report)
        return {} # Kita kembalikan kosong saja agar tidak ada keraguan

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
        domain = self._get_base_domain()
        action = {
            'name': 'Laporan Buku Besar',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'views': [(False, 'tree'), (False, 'form')],
            'domain': domain,
        }
        return action
    
    # FUNGSI EXPORT YANG DIMODIFIKASI TOTAL
    def export_report(self):
        """Fungsi BARU untuk Export Laporan ke CSV yang mengabaikan Saldo Awal."""
        self.ensure_one()
        
        # 1. Tentukan domain filter untuk transaksi yang akan diexport
        base_domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('move_id.state', '=', 'posted')
        ]
        
        # 2. Ambil SEMUA data yang difilter dalam rentang tanggal
        lines = self.env['account.move.line'].search(base_domain, order='date asc, id asc')

        # 3. Proses data dan hitung Cumulated Balance (DIMULAI DARI NOL)
        current_balance = {} # Inisialisasi saldo kumulatif global
        output = io.StringIO()
        
        # Header CSV (menggunakan koma sebagai delimiter, dengan quoting)
        output.write('"Akun","Tanggal","Jurnal","Nomor Referensi","Deskripsi","Debit","Kredit","Saldo Kumulatif"\n') 
        
        for account_id in self.account_ids.ids:
            account = self.env['account.account'].browse(account_id)
            
            # --- SALDO AWAL DIABAIKAN DI SINI ---
            
            # --- Filter baris transaksi hanya untuk akun ini ---
            account_lines = lines.filtered(lambda l: 
                l.account_id.id == account_id and 
                (not self.journal_ids or l.journal_id.id in self.journal_ids.ids)
            )
            
            # Reset current_balance untuk akun ini ke NOL (0.0)
            current_balance[account_id] = 0.0 

            for line in account_lines:
                # Update saldo kumulatif untuk akun ini, dimulai dari 0.0
                current_balance[account_id] += line.debit - line.credit
                
                # Gunakan quoting CSV untuk deskripsi dan referensi
                desc = line.name.replace('"', '""') if line.name else '' 
                ref = line.ref.replace('"', '""') if line.ref else line.move_id.name.replace('"', '""')
                
                row = [
                    line.account_id.display_name,
                    line.date.strftime('%Y-%m-%d'),
                    line.journal_id.name,
                    ref,
                    desc,
                    f"{line.debit:.2f}",
                    f"{line.credit:.2f}",
                    f"{current_balance[account_id]:.2f}"
                ]
                
                # Gunakan , sebagai delimiter dan sertakan tanda kutip untuk semua item
                quoted_row = [f'"{item}"' for item in row]
                output.write(','.join(quoted_row) + '\n') 

        # 4. Siapkan file untuk diunduh (tetap sama)
        report_data = base64.b64encode(output.getvalue().encode('utf-8'))
        
        self.write({
            'report_file': report_data,
            'file_name': 'Laporan_Buku_Besar.csv',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/report_file/Laporan_Buku_Besar.csv?download=true',
            'target': 'new',
        }
