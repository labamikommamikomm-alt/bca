# -*- coding: utf-8 -*-
{
    'name': 'Odoo Automated Year-End Closing Agent',
    'version': '14.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Automate fiscal year-end closing process',
    'description': """
        This module automates the process of closing the fiscal year in Odoo.
        It zeroes out nominal accounts (Income and Expense) and moves the 
        balance to the Retained Earnings account.
    """,
    'author': 'Antigravity',
    'depends': ['account', 'base_accounting_kit'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/account_closing_wizard_views.xml',
        'views/res_config_settings_views.xml',
        'views/account_closing_views.xml',
    ],
    'installable': True,
    'application': False,
}
