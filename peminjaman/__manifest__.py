# peminjaman/__manifest__.py
{
    'name': 'Peminjaman & Pengembalian Barang',
    'version': '1.0',
    'category': 'Sales/Purchase',
    'summary': 'Menambahkan fungsionalitas peminjaman dan pengembalian barang pada Sales/Purchase Order, Invoice/Bill.',
    'description': """
        Modul ini memungkinkan flagging transaksi sebagai peminjaman atau pengembalian
        pada Sales Order, Purchase Order, Invoice, dan Vendor Bill,
        dengan mengatur harga menjadi nol secara otomatis.
        Juga menyediakan laporan untuk melacak transaksi peminjaman dan pengembalian.
    """,
    'author': 'Your Name',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'sale_management',
        'purchase',
        'account',
        'stock', # Needed for product UoM and potentially stock moves in the future
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/account_move_views.xml',
        'views/create_borrow_po_wizard_views.xml',
        'views/create_return_so_wizard_views.xml',
        'views/borrow_report_wizard_views.xml',
        'reports/borrow_report_actions.xml',
        'reports/borrow_report_templates.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}