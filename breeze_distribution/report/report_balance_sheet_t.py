# nama_modul/report/__init__.py

from odoo import api, models, fields
from datetime import date
import calendar

class ReportBalanceSheetT(models.AbstractModel):
    _name = 'report.breeze_distribution.report_balance_sheet_t'
    _description = 'Laporan Neraca Format T'

    def _get_periods(self, data):
        """Menentukan daftar tanggal akhir dan header kolom berdasarkan input wizard."""
        end_dates = []
        column_headers = []
        month_names = {
            '1': 'Jan', '2': 'Feb', '3': 'Mar', '4': 'Apr', '5': 'Mei', '6': 'Jun',
            '7': 'Jul', '8': 'Agu', '9': 'Sep', '10': 'Okt', '11': 'Nov', '12': 'Des'
        }

        if data.get('filter_type') == 'standar':
            date_to = fields.Date.from_string(data.get('date_to'))
            end_dates.append(date_to)
            column_headers.append(date_to.strftime('%d %b %Y'))
        
        elif data.get('filter_type') == 'multi':
            if data.get('multi_period_type') == 'monthly':
                year = int(data.get('year_for_month'))
                month_from = int(data.get('month_from'))
                month_to = int(data.get('month_to'))
                for month in range(month_from, month_to + 1):
                    last_day = calendar.monthrange(year, month)[1]
                    end_dates.append(date(year, month, last_day))
                    column_headers.append(f"{month_names[str(month)]} {year}")
            
            elif data.get('multi_period_type') == 'yearly':
                year = int(data.get('year_selection'))
                for i in range(3):
                    current_year = year - i
                    end_dates.append(date(current_year, 12, 31))
                    column_headers.append(str(current_year))
        
        return end_dates, column_headers

    def _calculate_balances(self, end_date, company):
        """Menghitung saldo untuk satu tanggal tertentu."""
        fiscal_date = company.compute_fiscalyear_dates(end_date)
        date_from = fiscal_date['date_from']
        
        # === Query untuk Laba (Rugi) Tahun Berjalan (LENGKAP) ===
        query_profit_loss = """
            SELECT COALESCE(SUM(aml.credit) - SUM(aml.debit), 0) as balance
            FROM account_move_line aml
            JOIN account_account aa ON aml.account_id = aa.id
            JOIN account_account_type aat ON aa.user_type_id = aat.id
            WHERE aat.internal_group IN ('income', 'expense')
              AND aml.date BETWEEN %s AND %s
              AND aml.company_id = %s;
        """
        self.env.cr.execute(query_profit_loss, (date_from, end_date, company.id))
        current_year_earning = self.env.cr.dictfetchone().get('balance', 0.0)
        
        # === Query untuk semua akun Neraca (LENGKAP) ===
        # Menambahkan aa.id di SELECT dan GROUP BY untuk proses data
        query = """
            SELECT
                aa.id,
                aa.code,
                aa.name,
                aat.internal_group as internal_group,
                COALESCE(SUM(aml.debit) - SUM(aml.credit), 0) as balance
            FROM
                account_account aa
            JOIN
                account_account_type aat ON (aa.user_type_id = aat.id)
            LEFT JOIN
                account_move_line aml ON (aa.id = aml.account_id AND aml.date <= %s AND aml.company_id = %s)
            WHERE
                aat.internal_group IN ('asset', 'liability', 'equity')
            GROUP BY
                aa.id, aat.internal_group
            HAVING
                COALESCE(SUM(aml.debit) - SUM(aml.credit), 0) != 0
            ORDER BY
                aa.code;
        """
        self.env.cr.execute(query, (end_date, company.id))
        results = self.env.cr.dictfetchall()
        
        return results, current_year_earning

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data if data is not None else {}
        company = self.env.company
        
        end_dates, column_headers = self._get_periods(data)
        num_periods = len(end_dates)

        # Struktur untuk menampung data akun dari semua periode
        accounts_data = {}
        earnings_per_period = []
        assets_per_period = [0.0] * num_periods
        liabilities_equity_per_period = [0.0] * num_periods

        for i, end_date in enumerate(end_dates):
            results, current_year_earning = self._calculate_balances(end_date, company)
            earnings_per_period.append(current_year_earning)

            for res in results:
                acc_id = res['id']
                if acc_id not in accounts_data:
                    accounts_data[acc_id] = {
                        'name': res['name'],
                        'code': res['code'],
                        'internal_group': res['internal_group'],
                        'balances': [0.0] * num_periods
                    }
                
                balance = res['balance']
                if res['internal_group'] in ('liability', 'equity'):
                    balance = -balance

                accounts_data[acc_id]['balances'][i] = balance

                if res['internal_group'] == 'asset':
                    assets_per_period[i] += res['balance']
                else:
                    liabilities_equity_per_period[i] += balance
            
            liabilities_equity_per_period[i] += current_year_earning

        # Mengelompokkan data untuk template
        report_data = {
            'aktiva_lancar': {'lines': [], 'subtotals': [0.0] * num_periods},
            'aktiva_tetap': {'lines': [], 'subtotals': [0.0] * num_periods},
            'hutang_lancar': {'lines': [], 'subtotals': [0.0] * num_periods},
            'hutang_jangka_panjang': {'lines': [], 'subtotals': [0.0] * num_periods},
            'modal': {'lines': [], 'subtotals': [0.0] * num_periods},
        }

        for acc_id, acc_info in sorted(accounts_data.items(), key=lambda item: item[1]['code']):
            code = acc_info['code']
            group = acc_info['internal_group']
            
            line_data = {'name': acc_info['name'], 'balances': acc_info['balances']}
            target = None

            if group == 'asset':
                if code.startswith('11'):
                    target = report_data['aktiva_lancar']
                else: # Asumsi sisanya adalah aktiva tetap
                    target = report_data['aktiva_tetap']
            elif group == 'liability':
                if code.startswith('21'):
                    target = report_data['hutang_lancar']
                else: # Asumsi sisanya hutang jangka panjang
                    target = report_data['hutang_jangka_panjang']
            elif group == 'equity':
                target = report_data['modal']

            if target:
                target['lines'].append(line_data)
                for i in range(num_periods):
                    target['subtotals'][i] += acc_info['balances'][i]

        # Menambahkan laba tahun berjalan ke subtotal modal
        for i in range(num_periods):
            report_data['modal']['subtotals'][i] += earnings_per_period[i]

        # Menentukan tanggal yang akan ditampilkan di header
        display_date = data.get('date_to') if data.get('filter_type') == 'standar' else fields.Date.to_string(date.today())

        return {
            'doc_ids': docids,
            'doc_model': 'balance.sheet.t.wizard',
            'company': company,
            'date_to': display_date,
            'data': report_data,
            'column_headers': column_headers,
            'is_multi_period': data.get('filter_type') == 'multi',
            'current_year_earnings': earnings_per_period,
            'total_assets_per_period': assets_per_period,
            'total_liabilities_equity_per_period': liabilities_equity_per_period,
        }