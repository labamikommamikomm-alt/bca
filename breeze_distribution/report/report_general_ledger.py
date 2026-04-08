# nama_modul/report/report_general_ledger.py

from odoo import api, models, fields
from datetime import date, timedelta
import calendar
from collections import OrderedDict

class ReportGeneralLedger(models.AbstractModel):
    _name = 'report.breeze_distribution.report_general_ledger'
    _description = 'Laporan Buku Besar'

    def _get_periods(self, data):
        # ... (Fungsi ini tidak berubah, biarkan seperti sebelumnya) ...
        periods = []
        column_headers = []
        month_names = {'1': 'Jan', '2': 'Feb', '3': 'Mar', '4': 'Apr', '5': 'Mei', '6': 'Jun', '7': 'Jul', '8': 'Agu', '9': 'Sep', '10': 'Okt', '11': 'Nov', '12': 'Des'}
        if data.get('filter_type') == 'standar':
            date_from = fields.Date.from_string(data.get('date_from'))
            date_to = fields.Date.from_string(data.get('date_to'))
            periods.append({'start': date_from, 'end': date_to})
            column_headers.append(date_to.strftime('%d %b %Y'))
        elif data.get('filter_type') == 'multi':
            if data.get('multi_period_type') == 'monthly':
                year, month_from, month_to = int(data.get('year_for_month')), int(data.get('month_from')), int(data.get('month_to'))
                for month in range(month_from, month_to + 1):
                    periods.append({'start': date(year, month, 1), 'end': date(year, month, calendar.monthrange(year, month)[1])})
                    column_headers.append(f"{month_names[str(month)]} {year}")
            elif data.get('multi_period_type') == 'yearly':
                year = int(data.get('year_selection'))
                for i in range(3):
                    current_year = year - i
                    periods.append({'start': date(current_year, 1, 1), 'end': date(current_year, 12, 31)})
                    column_headers.append(str(current_year))
        return periods, column_headers

    @api.model
    def _get_report_values(self, docids, data=None):
        company = self.env.company
        periods, column_headers = self._get_periods(data)
        display_mode = 'summary' if data.get('filter_type') == 'multi' else data.get('display_mode')
        
        account_domain = [('company_id', '=', company.id)]
        if data.get('account_type_ids'):
            account_domain.append(('user_type_id', 'in', data.get('account_type_ids')))
        
        accounts = self.env['account.account'].search(account_domain, order='code')
        
        # ### PERUBAHAN UTAMA: Gunakan dictionary untuk mengelompokkan ###
        grouped_lines = OrderedDict()

        for account in accounts:
            # Lewati akun view yang tidak memiliki tipe
            if not account.user_type_id:
                continue

            account_data = {
                'code': account.code,
                'name': account.name,
                'ending_balances': []
            }

            has_movement = False
            for period in periods:
                date_from = period['start']
                date_to = period['end']
                
                prev_period_end = date_from - timedelta(days=1)
                self.env.cr.execute("SELECT COALESCE(SUM(balance), 0) FROM account_move_line WHERE account_id = %s AND date <= %s AND parent_state = 'posted'", (account.id, prev_period_end))
                begin_balance = self.env.cr.fetchone()[0]
                
                self.env.cr.execute("SELECT COALESCE(SUM(balance), 0) FROM account_move_line WHERE account_id = %s AND date <= %s AND parent_state = 'posted'", (account.id, date_to))
                end_balance = self.env.cr.fetchone()[0]

                # Tampilkan akun jika ada saldo awal, atau ada pergerakan di periode berjalan
                move_lines = self.env['account.move.line'].search([('account_id', '=', account.id), ('date', '>=', date_from), ('date', '<=', date_to), ('parent_state', '=', 'posted')])
                if begin_balance != 0 or move_lines:
                    has_movement = True

                account_data['ending_balances'].append(end_balance)

                if display_mode == 'detail':
                    account_data.update({
                        'begin_balance': begin_balance,
                        'lines': move_lines,
                        'total_debit': sum(line.debit for line in move_lines),
                        'total_credit': sum(line.credit for line in move_lines),
                    })
            
            if has_movement:
                # ### PERUBAHAN UTAMA: Masukkan data ke dalam grupnya ###
                type_name = account.user_type_id.name
                if type_name not in grouped_lines:
                    grouped_lines[type_name] = []
                grouped_lines[type_name].append(account_data)

        return {
            'company': company,
            'grouped_lines': grouped_lines, # Kirim data yang sudah dikelompokkan
            'column_headers': column_headers,
            'display_mode': display_mode,
        }