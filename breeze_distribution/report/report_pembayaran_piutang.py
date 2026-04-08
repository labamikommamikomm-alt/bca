# nama_modul/report/report_profit_loss.py

from odoo import api, models, fields
from datetime import date, timedelta
import calendar

class ReportProfitLoss(models.AbstractModel):
    _name = 'report.breeze_distribution.report_profit_loss'
    _description = 'Laporan Laba Rugi'

    def _get_periods(self, data):
        periods = []
        column_headers = []
        month_names = {
            '1': 'Jan', '2': 'Feb', '3': 'Mar', '4': 'Apr', '5': 'Mei', '6': 'Jun',
            '7': 'Jul', '8': 'Agu', '9': 'Sep', '10': 'Okt', '11': 'Nov', '12': 'Des'
        }

        if data.get('filter_type') == 'standar':
            date_from = fields.Date.from_string(data.get('date_from'))
            date_to = fields.Date.from_string(data.get('date_to'))
            periods.append({'start': date_from, 'end': date_to})
            column_headers.append(date_to.strftime('%d %b %Y'))
        
        elif data.get('filter_type') == 'multi':
            if data.get('multi_period_type') == 'monthly':
                year = int(data.get('year_for_month'))
                month_from = int(data.get('month_from'))
                month_to = int(data.get('month_to'))
                for month in range(month_from, month_to + 1):
                    start_date = date(year, month, 1)
                    end_date = date(year, month, calendar.monthrange(year, month)[1])
                    periods.append({'start': start_date, 'end': end_date})
                    column_headers.append(f"{month_names[str(month)]} {year}")
            
            elif data.get('multi_period_type') == 'yearly':
                year = int(data.get('year_selection'))
                for i in range(3):
                    current_year = year - i
                    start_date = date(current_year, 1, 1)
                    end_date = date(current_year, 12, 31)
                    periods.append({'start': start_date, 'end': end_date})
                    column_headers.append(str(current_year))
        
        return periods, column_headers

    def _calculate_balances_for_period(self, date_from, date_to, company_id):
        """Menghitung saldo dan mengelompokkan berdasarkan Tipe Akun."""
        B_LAIN_NAME = 'lainnya' 
        PAJAK_NAME = 'pph'
        
        query = """
            SELECT
                aa.code,
                aa.name,
                aat.name as type_name,
                COALESCE(SUM(aml.credit - aml.debit), 0) as balance
            FROM account_move_line aml
            JOIN account_account aa ON aml.account_id = aa.id
            JOIN account_account_type aat ON aa.user_type_id = aat.id
            WHERE aat.internal_group IN ('income', 'expense')
              AND aml.date BETWEEN %s AND %s
              AND aml.company_id = %s
            GROUP BY aa.id, aat.name
            HAVING COALESCE(SUM(aml.credit - aml.debit), 0) != 0
            ORDER BY aa.code;
        """
        self.env.cr.execute(query, (date_from, date_to, company_id))
        results = self.env.cr.dictfetchall()
        
        period_data = {
            'penjualan_usaha': 0.0,
            'pendapatan_lain': 0.0,
            'hpp': 0.0,
            'beban_usaha_details': [],
            'beban_lain': 0.0,
            'pajak': 0.0,
        }

        for res in results:
            type_name = res['type_name']
            name = res['name'].lower()
            balance = res['balance']
            
            if type_name == 'Income':
                period_data['penjualan_usaha'] += balance
            elif type_name == 'Other Income':
                period_data['pendapatan_lain'] += balance
            elif type_name == 'Cost of Revenue':
                period_data['hpp'] -= balance
            elif type_name in ('Expense', 'Expenses', 'Depreciation'):
                if B_LAIN_NAME in name:
                    period_data['beban_lain'] -= balance
                elif PAJAK_NAME in name:
                    period_data['pajak'] -= balance
                else:
                    period_data['beban_usaha_details'].append({
                        'code': res['code'],
                        'name': res['name'],
                        'balance': -balance
                    })
        
        return period_data

    @api.model
    def _get_report_values(self, docids, data=None):
        periods, column_headers = self._get_periods(data)
        num_periods = len(column_headers)

        report_data = {
            'penjualan': {'balances': [0.0] * num_periods},
            'hpp': {'balances': [0.0] * num_periods},
            'pendapatan_lain': {'balances': [0.0] * num_periods},
            'biaya_lain': {'balances': [0.0] * num_periods},
            'pajak': {'balances': [0.0] * num_periods},
        }
        all_period_expenses = [] 

        for i, period in enumerate(periods):
            period_balances = self._calculate_balances_for_period(period['start'], period['end'], self.env.company.id)
            
            report_data['penjualan']['balances'][i] = period_balances['penjualan_usaha']
            report_data['hpp']['balances'][i] = period_balances['hpp']
            report_data['pendapatan_lain']['balances'][i] = period_balances['pendapatan_lain']
            report_data['biaya_lain']['balances'][i] = period_balances['beban_lain']
            report_data['pajak']['balances'][i] = period_balances['pajak']
            all_period_expenses.append(period_balances['beban_usaha_details'])
        
        all_expenses_map = {}
        for period_expenses in all_period_expenses:
            for exp in period_expenses:
                if exp['code'] not in all_expenses_map:
                    all_expenses_map[exp['code']] = {'name': exp['name']}
        
        sorted_expense_codes = sorted(all_expenses_map.keys())

        expense_details_list = []
        for code in sorted_expense_codes:
            line = {'code': code, 'name': all_expenses_map[code]['name'], 'balances': []}
            for period_expenses in all_period_expenses:
                balance = next((item['balance'] for item in period_expenses if item['code'] == code), 0.0)
                line['balances'].append(balance)
            expense_details_list.append(line)

        return {
            'company': self.env.company,
            'data': report_data,
            'expense_details': expense_details_list,
            'column_headers': column_headers,
            'num_periods': len(column_headers),
        }