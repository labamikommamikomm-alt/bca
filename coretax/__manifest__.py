# l10n_id_coretax/__manifest__.py
{
    'name': 'Coretax',
    'version': '1.3',
    'summary': 'Export Odoo Invoices to Coretax XLSX format.',
    'description': """
        This module enhances Odoo's accounting functionality to comply with
        Indonesian Coretax requirements. It allows users to export Customer Invoices
        to a multi-sheet XLSX file containing Faktur, DetailFaktur, REF, and Keterangan sheets.
    """,
    'author': 'Adrian',
    'category': 'Accounting/Localizations',
    'license': 'LGPL-3',
    'depends': ['account', 'product', 'uom', 'l10n_id'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/product_template_views.xml',
        'views/uom_uom_views.xml',
        'wizard/export_coretax_wizard_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },
}